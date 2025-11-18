# AnonCreds Revocation: Event-driven auto-recovery

This document explains how the new event-driven revocation workflow works, and how ACA-Py automatically recovers from partial failures when managing AnonCreds revocation registries.

The intention is:

* **Issuers should not have to manually repair broken revocation registries** in normal operation.
* **Revocation operations should be resilient** to:

  * transient ledger / tails server errors,
  * database errors, and
  * abrupt agent shutdowns (e.g., container restarts).

## Scope

This mechanism applies to **AnonCreds revocation** for credential definitions managed by ACA-Py, specifically:

* Creating initial revocation registries when a **credential definition is finished**.
* Handling **revocation registries that become full**, by:

  * activating the backup registry, and
  * creating a new backup registry.

## High-level overview

The revocation lifecycle is now modeled as a series of **events**. Each event:

1. Has a **request** (e.g. “create revocation registry definition”),
2. Has a corresponding **response** (success or failure), and
3. Is **persisted** to storage so it can be retried or recovered later.

At a high level:

1. When a revocation-related action is needed, ACA-Py:

   * creates an **event record** in storage,
   * emits a **request event** on the internal event bus.
2. A handler processes the event and:

   * on success:

     * updates the event record,
     * emits the **next event** in the chain (if any),
   * on failure:

     * records error and retry metadata,
     * marks whether the event should be **retried**.
3. If the agent restarts or an event fails:

   * **EventRecoveryManager** scans event records and re-emits eligible events for retry.
   * Recovery is triggered by an **admin middleware** when the profile is first used.

This ensures that partial progress (e.g., a registry created on ledger but not activated locally) can be revisited and completed.

## Key concepts & terminology

### Event types

Revocation workflows are broken down into more granular events. The most important ones are:

#### Revocation registry definition

* `anoncreds::rev-reg-def::create-requested`
* `anoncreds::rev-reg-def::create-response`
* `anoncreds::rev-reg-def::store-requested`
* `anoncreds::rev-reg-def::store-response`

#### Revocation status list (revocation list)

* `anoncreds::revocation-list::create-requested`
* `anoncreds::revocation-list::create-response`
* `anoncreds::revocation-list::store-requested`
* `anoncreds::revocation-list::store-response`
* `anoncreds::revocation-list::finished`
  (kept for compatibility; now effectively the “end” of the setup chain)

#### Registry activation & full handling

* `anoncreds::revocation-registry::activation-requested`
* `anoncreds::revocation-registry::activation-response`
* `anoncreds::revocation-registry::full-detected`
* `anoncreds::revocation-registry::full-handling-completed`

Each event carries:

* A **payload** (what to do, and with which IDs),
* `options` (metadata such as `request_id`, `correlation_id`, `retry_count`, `recovery` flag, and any other method-specific options).

### Event records in storage

Each revocation event is represented by a storage record with:

* **Type** — one of:

  * `rev_reg_def_create_event`
  * `rev_reg_def_store_event`
  * `rev_list_create_event`
  * `rev_list_store_event`
  * `rev_reg_activation_event`
  * `rev_reg_full_handling_event`
* **State** — one of:

  * `requested`
  * `response_success`
  * `response_failure`
* **Metadata**, including:

  * `event_type` (the topic name),
  * `correlation_id` (used as a stable key across request/response),
  * `request_id` (optional),
  * serialized `event_data` (payload + options),
  * `response_data` (for responses),
  * `error_msg` and `retry_metadata` (if a failure occurs),
  * `expiry_timestamp` (when the event becomes eligible for recovery).

These records allow ACA-Py to see:

* which operations are **in progress**,
* which have **failed but can be retried**, and
* which are **complete**.

## Lifecycle: initial revocation setup

When a credential definition is **successfully created** and ready for revocation:

1. **Cred def finished → create revocation registry definition**

   * `CredDefFinishedEvent` triggers `DefaultRevocationSetup`.
   * A **revocation registry definition create event** is stored:

     * record type: `rev_reg_def_create_event`
     * state: `requested`
   * ACA-Py emits:
     `anoncreds::rev-reg-def::create-requested`

2. **Create revocation registry definition (ledger)**

   * Handler receives `create-requested` and attempts to:

     * create the revocation registry definition on the ledger.
   * On success:

     * Updates event record → `response_success`,
     * Emits: `anoncreds::rev-reg-def::create-response`,
     * Then creates & stores a **store event**: `rev_reg_def_store_event`,
     * Emits: `anoncreds::rev-reg-def::store-requested`.
   * On failure:

     * Updates event record → `response_failure`,
     * Adds `error_msg` + `retry_metadata` (including `should_retry`).
     * No subsequent events are emitted until a retry or recovery occurs.

3. **Store revocation registry definition (local)**

   * Handler receives `store-requested` and attempts to store locally.
   * On success:

     * Updates event record → `response_success`,
     * Emits: `anoncreds::rev-reg-def::store-response`,
     * Creates & emits **revocation list create** event:

       * `rev_list_create_event`,
       * `anoncreds::revocation-list::create-requested`.
   * On failure:

     * Stores error and marks failure with `response_failure`,
     * Recovery mechanism can later retry this event.

4. **Create revocation list**

   * Handler receives `revocation-list::create-requested` and:

     * creates the revocation status list (revocation list) for this registry.
   * On success:

     * Marks event as `response_success`,
     * Emits `revocation-list::create-response`,
     * Creates & emits **revocation list store** event:

       * `rev_list_store_event`,
       * `anoncreds::revocation-list::store-requested`.
   * On failure:

     * Marks event as `response_failure` with retry metadata.

5. **Store revocation list & finish**

   * Handler receives `revocation-list::store-requested` and attempts to store:

     * revocation list locally and/or in the tails server (depending on implementation).
   * On success:

     * Marks event as `response_success`,
     * Emits `anoncreds::revocation-list::store-response`,
     * Finally emits: `anoncreds::revocation-list::finished`.
   * On failure:

     * Marks event with `response_failure` and retry metadata.

6. **Activate registry**

   * In many cases, part of the setup chain is to **activate** the revocation registry:

     * event type: `rev_reg_activation_event`,
     * topic: `anoncreds::revocation-registry::activation-requested`.
   * On success:

     * Marks `rev_reg_activation_event` as `response_success`,
     * Emits `activation-response`,
     * The registry is now active and ready for issuance.
   * On failure:

     * Marks `response_failure` and leaves it to recovery / retry.

**Important:** Every step that can fail has:

* a **stored event record**, and
* a clear **request/response event pair**, designed for safe retry.

## Lifecycle: handling a full revocation registry

When a revocation registry reaches capacity, the following should happen:

1. **Full detected**

   * ACA-Py detects that the current registry is full:

     * event type: `rev_reg_full_handling_event`,
     * topic: `anoncreds::revocation-registry::full-detected`.
   * It marks the current registry as **FULL** and stores a full-handling event.

2. **Activate backup registry**

   * Part of full handling is to **activate** the backup registry (if present):

     * request event: `anoncreds::revocation-registry::activation-requested` (with correlation metadata tying it to full handling).
   * On success:

     * Response event marks activation with `response_success`.
   * On failure:

     * Response event records failure/error with `response_failure` + retry metadata.

3. **Create new backup registry**

   * Once the backup registry is activated, ACA-Py initiates the creation of a **new backup registry** (using the same event chain as the initial setup: rev-reg-def / revocation-list events).
   * All steps are fully event-driven and persisted in the same way:

     * create & store rev-reg-def,
     * create & store revocation list,
     * activate new backup.

4. **Full handling completed**

   * When activation and new backup creation are done, ACA-Py emits:

     * `anoncreds::revocation-registry::full-handling-completed`.
   * At this point:

     * the previously “backup” registry is now active, and
     * a new backup registry exists,
     * the credential definition remains usable for future issuance.

If any of these steps fail, the failure is recorded as a stored event and becomes eligible for retry/recovery, instead of silently leaving the credential definition without a usable revocation registry.

## Failure handling & retries

### Error information

When a handler processes a **response** event and encounters an error, it can attach an `ErrorInfoPayload` to the event response that includes:

* `error_msg` — human-readable description of what went wrong.
* `should_retry` — whether this failure is expected to be transient.
* `retry_count` — how many times this operation has been retried so far.

The event record is then stored with:

* `state = response_failure`,
* `retry_metadata` (including most recent `retry_count` and calculated delay),
* `expiry_timestamp` — the time at which this failed event should be considered “expired” and eligible for recovery.

### Exponential backoff

Retry timing is calculated using exponential backoff, controlled via environment variables:

* `ANONCREDS_REVOCATION_MIN_RETRY_DURATION_SECONDS`
  **Default:** `2`
  Initial delay (e.g. 2 seconds).
* `ANONCREDS_REVOCATION_MAX_RETRY_DURATION_SECONDS`
  **Default:** `60`
  Maximum delay cap.
* `ANONCREDS_REVOCATION_RETRY_MULTIPLIER`
  **Default:** `2.0`
  Multiplier applied per retry (e.g. 2 → 4 → 8 → 16 seconds… up to the max).

The general pattern is:

```text
delay_for_retry_n = min(
    max_retry_duration,
    min_retry_duration * (multiplier ** retry_count)
)
```

### Event expiry & recovery delay

A separate setting controls **when** an event becomes eligible for recovery:

* `ANONCREDS_REVOCATION_RECOVERY_DELAY_SECONDS`
  **Default:** `30`

This is used to compute an `expiry_timestamp` for each failed event. Once the current time passes the expiry timestamp, the event is treated as **expired** and can be re-emitted by the recovery mechanism.

## Recovery flow

Recovery is handled by two components:

1. **EventStorageManager**
2. **EventRecoveryManager + admin middleware**

### EventStorageManager

This is the persistence layer for revocation events. Core behaviours:

* **store_event_request(...)**

  * Creates a new event record in state `requested`.
* **update_event_response(...)**

  * Updates event with success/failure, response payload, error info, and retry metadata.
* **update_event_for_retry(...)**

  * Moves a failed event back to `requested`,
  * increments `retry_count`,
  * computes a new `expiry_timestamp`.
* **get_in_progress_events(...)**

  * Returns events that:

    * are still in progress, or
    * have failed but not been cleaned up yet.
* **delete_event(...)**

  * Removes event records that are no longer needed.

### EventRecoveryManager

The `EventRecoveryManager` is responsible for **finding stuck events** and re-emitting them:

1. Fetches all **in-progress** or failed events from `EventStorageManager`.
2. Filters those whose `expiry_timestamp` has passed (i.e., ready for recovery).
3. For each expired event:

   * Marks the event for retry (updating retry count and expiry),
   * Reconstructs the original **request event** and:

     * emits it on the event bus with:

       * the original `correlation_id`,
       * `options["recovery"] = true`.

The fact that `recovery = true` is part of the options lets handlers distinguish between **normal flow** and **recovery flow**, if needed (for logging, special handling, etc.).

### Admin middleware: triggering recovery per profile

Recovery is triggered automatically by the **revocation recovery middleware**, which is added to the admin server.

On each admin request:

1. The middleware resolves the **current profile/tenant**.
2. If recovery has **not yet run** for this profile:

   * It calls `EventRecoveryManager.recover_in_progress_events(...)` for that profile.
   * Marks that profile as “recovered” for the lifetime of this server process (so recovery is only run once per profile per process start).
3. Any errors during recovery are logged but **do not block** the admin request.

This gives the following behavior:

* When the agent process restarts, the **first admin call per profile** triggers recovery of any stuck revocation events for that profile.
* After that, normal admin operations proceed without additional recovery overhead, unless the process restarts again.

## Operational notes

### What operators should expect

* In normal operation, **no manual action is needed**. Revocation setup and full-registry handling should be:

  * automatic,
  * retried with backoff on transient errors,
  * recovered after restarts.
* When persistent errors occur (e.g., misconfiguration, invalid ledger state), events may:

  * exhaust their retries, and
  * be logged with errors indicating that **manual intervention is required**.

### Logging & monitoring

You can monitor logs to see:

* When events are:

  * created,
  * retried,
  * successfully completed.
* When errors occur during:

  * ledger interactions,
  * local storage operations,
  * tails server uploads.
* When the **recovery middleware** runs and which events are recovered.

If a credential definition becomes unusable, logs should contain:

* the associated `correlation_id`,
* the failing event type,
* a human-readable `error_msg`,
* information about whether the operation is still being retried or has given up.

### Tuning behavior

You can adjust:

* **Retry timing and backoff** using:

  * `ANONCREDS_REVOCATION_MIN_RETRY_DURATION_SECONDS`
  * `ANONCREDS_REVOCATION_MAX_RETRY_DURATION_SECONDS`
  * `ANONCREDS_REVOCATION_RETRY_MULTIPLIER`
* **Recovery delay** using:

  * `ANONCREDS_REVOCATION_RECOVERY_DELAY_SECONDS`

to match the behavior of your ledger network and tails infrastructure (e.g., slower networks may benefit from larger delay and max).

## Summary

With this event-driven auto-recovery mechanism:

* Each revocation operation is **tracked as a persistent event**.
* Failures are **captured, retried with backoff**, and **eligible for recovery** after a delay.
* Abrupt agent restarts no longer leave revocation registries in silent broken states.
* The **first admin request per profile** after a restart acts as a trigger to resume any incomplete revocation workflows.

This greatly reduces the chances that a credential definition becomes silently unusable due to revocation registry issues, and it provides clearer logging and hooks for operators when manual intervention is needed.
