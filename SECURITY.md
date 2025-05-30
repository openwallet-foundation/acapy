# ACA-Py Security Policy

## About this Document

This document document defines how security vulnerability reporting is handled
in this project. The approach aligns with the [OpenWallet Foundation's security vulnerability disclosure policy].
Please review that document to understand
the basis of the security reporting for this project

This policy borrows heavily from the recommendations of the OpenSSF
Vulnerability Disclosure working group. For up-to-date information on the latest
recommendations related to vulnerability disclosures, please visit the [GitHub
of that working group](https://github.com/ossf/wg-vulnerability-disclosures).

If you are already familiar with what a security vulnerability disclosure policy
is and are ready to report a vulnerability, please jump to [Report
Intakes](#report-intakes).

[OpenWallet Foundation's security vulnerability disclosure policy]: https://tac.openwallet.foundation/governance/security/

## What Is a Vulnerability Disclosure Policy?

No piece of software is perfect. All software (at least, all software of a
certain size and complexity) has bugs. In open source development, members of
the community or the public find bugs and report them to the project. A
vulnerability disclosure policy explains how this process functions from the
perspective of the project.

This vulnerability disclosure policy explains the rules and guidelines for
this project. It is intended to act as both a reference for
outsiders–including both bug reporters and those looking for information on the
project’s security practices–as well as a set of rules that maintainers and
contributors have agreed to follow.

## Report Intakes

This project uses the following mechanism to submit security
vulnerabilities. While the security team members will do their best to
respond to bugs disclosed in all possible ways, it is encouraged for bug
finders to report through the following approved channel:

- Open a [GitHub security vulnerability report]: Open a new draft security
  advisory from the [Security
  Advisories](https://github.com/openwallet-foundation/acapy/security/advisories)
  of the ACA-Py repository. See [GitHub Security
  Advisories](#github-security-advisories) to learn more about the security
  infrastructure in GitHub.

[GitHub security vulnerability report]: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability

## Security Team

The current security team is:

| Name            | Email ID                   | OWF Discord Chat ID | Area/Specialty     |
| --------------- | -------------------------- | ------------------- | ------------------ |
| Stephen Curran  | swcurran@cloudcompass.ca   | swcurran            | Generalist         |
| Emiliano Sune   | emiliano.sune@quartech.com | esune               | Python             |
| Wade Barnes     | wade@neoterictech.ca       | wadebarnes          | GHA and Deployment |
| Mourits de Beer | mourits.debeer@didx.co.za  | friendlyfire137     | Python             |
| Jamie Hale      | jamie.hale@quartech.com    | jamshale            | Python             |

The security team for this project must include at least three project
Maintainers that agree to carry out the following duties and responsibilities.
Members are added and removed from the team via approved Pull Requests to this
repository. For additional background into the role of the security team, see
the [People Infrastructure] section of the [OpenWallet Foundation's security vulnerability disclosure policy].

[People Infrastructure]: https://tac.openwallet.foundation/governance/security#people-infrastructure

**Responsibilities**:

1. Acknowledge receipt of the issue (see [Report Intakes](#report-intakes)) to the reporter within 2 business days.

2. Assess the issue. Engage with the reporter to ask any outstanding questions about the report and how to reproduce it. If the report is not considered a vulnerability, then the reporter should be informed and this process can be halted. If the report is still a regular bug (just not a security vulnerability), the reporter should be informed (if necessary) of the regular process for reporting bugs.

3. Some issues may require more time and resources to correct. If a
particular report is more complex, discuss an embargo period with the reporter.
The embargo period should be negotiated with the reporter and must not be
longer than 90 days.

4. Create a patch for the issue (see [Private Patch Deployment
Infrastructure](#private-patch-deployment-infrastructure)).

5. Request a CVE for the issue (see [CNA/CVE Reporting](#cnacve-reporting)).

6. Decide the date of public release.

7. If applicable, notify members of the embargo list of the upcoming patch
and release, as described above.

8. Cut a new (software) release in which the bug is fixed.

9. Publicly disclose the issue within 48 hours after the release (see [GitHub Security Advisories](#github-security-advisories)).

## Discussion Forum

Discussions about each reported vulnerability are carried out in the
private GitHub security advisory about the vulnerability.
If necessary, a private channel specific to the issue may be created on the
OpenWallet Foundation's Discord server with invited participants added to the
discussion.

## CNA/CVE Reporting

This project maintains a list of **Common Vulnerabilities and Exposures
(CVE)** and uses GitHub as its **CVE numbering authority (CNA)** for issuing
CVEs.

## Embargo List

This project maintains a private embargo list.  If you wish to be added to the
embargo list for a project, please email the members of the Security team
(emails [above](#security-team)), including the project name and reason for
being added to the embargo list. Requests will be assessed by the security team
in conjunction with the appropriate OpenWallet Foundation staff, and a decision
will be made whether to accommodate the request.

## GitHub Security Advisories

This project uses [GitHub security advisories and the GitHub security process](https://docs.github.com/en/code-security/security-advisories) for handling security vulnerabilities. 

## Private Patch Deployment Infrastructure

In creating patches and new releases that address security vulnerabilities,
this project uses the private development features of GitHub for security
vulnerabilities. GitHub has [extensive
documentation](https://docs.github.com/en/code-security/security-advisories/repository-security-advisories)
about these features.
