# ACA-Py Unit Tests

The following covers the Unit Testing framework in ACA-Py, how to run the tests, and how to add unit tests.

This [video](https://youtu.be/yJ6LpAiVNFM) is a presentation of the material covered in this document by
developer @shaangill025.

## Running unit tests in ACA-Py

- `./scripts/run_tests`
- `./scripts/run_tests aries_clouadagent/protocols/out_of_band/v1_0/tests`
- `./scripts/run_tests_indy` includes Indy specific tests

## Pytest

Example: aries_cloudagent/core/tests/test_event_bus.py

```python
@pytest.fixture
def event_bus():
    yield EventBus()


@pytest.fixture
def profile():
    yield async_mock.MagicMock()


@pytest.fixture
def event():
    event = Event(topic="anything", payload="payload")
    yield event
    
class MockProcessor:
    def __init__(self):
        self.profile = None
        self.event = None

    async def __call__(self, profile, event):
        self.profile = profile
        self.event = event


@pytest.fixture
def processor():
    yield MockProcessor()
```

---

```python
def test_sub_unsub(event_bus: EventBus, processor):
    """Test subscribe and unsubscribe."""
    event_bus.subscribe(re.compile(".*"), processor)
    assert event_bus.topic_patterns_to_subscribers
    assert event_bus.topic_patterns_to_subscribers[re.compile(".*")] == [processor]
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers
```

From aries_cloudagent/core/event_bus.py

```python
class EventBus:
    def __init__(self):
        self.topic_patterns_to_subscribers: Dict[Pattern, List[Callable]] = {}

def subscribe(self, pattern: Pattern, processor: Callable):
        if pattern not in self.topic_patterns_to_subscribers:
            self.topic_patterns_to_subscribers[pattern] = []
        self.topic_patterns_to_subscribers[pattern].append(processor)

def unsubscribe(self, pattern: Pattern, processor: Callable):
    if pattern in self.topic_patterns_to_subscribers:
        try:
            index = self.topic_patterns_to_subscribers[pattern].index(processor)
        except ValueError:
            return
        del self.topic_patterns_to_subscribers[pattern][index]
        if not self.topic_patterns_to_subscribers[pattern]:
            del self.topic_patterns_to_subscribers[pattern]
```

---

```python
@pytest.mark.asyncio
async def test_sub_notify(event_bus: EventBus, profile, event, processor):
    """Test subscriber receives event."""
    event_bus.subscribe(re.compile(".*"), processor)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event
```

```python
async def notify(self, profile: "Profile", event: Event):
    partials = []
    for pattern, subscribers in self.topic_patterns_to_subscribers.items():
        match = pattern.match(event.topic)

        if not match:
            continue

        for subscriber in subscribers:
            partials.append(
                partial(
                    subscriber,
                    profile,
                    event.with_metadata(EventMetadata(pattern, match)),
                )
            )

    for processor in partials:
        try:
            await processor()
        except Exception:
            LOGGER.exception("Error occurred while processing event")
```

---

## asynctest

From: aries_cloudagent/protocols/didexchange/v1_0/tests/test.manager.py

```python
class TestDidExchangeManager(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.responder = MockResponder()

        self.oob_mock = async_mock.MagicMock(
            clean_finished_oob_record=async_mock.CoroutineMock(return_value=None)
        )

        self.route_manager = async_mock.MagicMock(RouteManager)
        ...
        self.profile = InMemoryProfile.test_profile(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
                "multitenant.enabled": True,
                "wallet.id": True,
            },
            bind={
                BaseResponder: self.responder,
                OobMessageProcessor: self.oob_mock,
                RouteManager: self.route_manager,
                ...
            },
        )
        ...
        
    async def test_receive_invitation_no_auto_accept(self):
        async with self.profile.session() as session:
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                self.multitenant_mgr, "get_default_mediator"
            ) as mock_get_default_mediator:
                mock_get_default_mediator.return_value = mediation_record
                invi_rec = await self.oob_manager.create_invitation(
                    my_endpoint="testendpoint",
                    hs_protos=[HSProto.RFC23],
                )

                invitee_record = await self.manager.receive_invitation(
                    invi_rec.invitation,
                    auto_accept=False,
                )
                assert invitee_record.state == ConnRecord.State.INVITATION.rfc23
```

---

```python
async def receive_invitation(
    self,
    invitation: OOBInvitationMessage,
    their_public_did: Optional[str] = None,
    auto_accept: Optional[bool] = None,
    alias: Optional[str] = None,
    mediation_id: Optional[str] = None,
) -> ConnRecord:
    ...
    accept = (
        ConnRecord.ACCEPT_AUTO
        if (
            auto_accept
            or (
                auto_accept is None
                and self.profile.settings.get("debug.auto_accept_invites")
            )
        )
        else ConnRecord.ACCEPT_MANUAL
    )
    service_item = invitation.services[0]
    # Create connection record
    conn_rec = ConnRecord(
        invitation_key=(
            DIDKey.from_did(service_item.recipient_keys[0]).public_key_b58
            if isinstance(service_item, OOBService)
            else None
        ),
        invitation_msg_id=invitation._id,
        their_label=invitation.label,
        their_role=ConnRecord.Role.RESPONDER.rfc23,
        state=ConnRecord.State.INVITATION.rfc23,
        accept=accept,
        alias=alias,
        their_public_did=their_public_did,
        connection_protocol=DIDX_PROTO,
    )

    async with self.profile.session() as session:
        await conn_rec.save(
            session,
            reason="Created new connection record from invitation",
            log_params={
                "invitation": invitation,
                "their_role": ConnRecord.Role.RESPONDER.rfc23,
            },
        )

        # Save the invitation for later processing
        ...

    return conn_rec
```

## Other details

- Error catching

```python
  with self.assertRaises(DIDXManagerError) as ctx:
     ...
  assert " ... error ..." in str(ctx.exception)
```
  
- function.`assert_called_once_with(parameters)`
  function.`assert_called_once()`
  
- pytest.mark setup in `setup.cfg`
  can be attributed at function or class level. Example, `@pytest.mark.indy`
  
- Code coverage
  ![Code coverage screenshot](https://i.imgur.com/VhNYcje.png)
