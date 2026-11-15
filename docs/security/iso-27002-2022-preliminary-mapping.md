# ISO/IEC 27002:2022 preliminary control mapping — ObStack

**Status:** preliminary technical mapping only. This is not an ISO audit, certification, statement of applicability, or organizational compliance assertion. It is based on repository configuration and design documents, not independently verified deployed controls. All entries remain Partial or Pending until the organization assigns control owners and evidence is verified.

**Scope:** the ObStack observability platform, its repository/CI, Ansible automation, future central EC2 host and enrolled remote servers. Organization-wide controls (policy, HR, physical/cloud provider governance, incident ownership, legal/privacy requirements) cannot be demonstrated by this repository alone.

## Preliminary mapping

| Control | Objective (brief paraphrase) | ObStack evidence | Verification method | Status | Responsibility / gap |
|---|---|---|---|---|---|
| 5.1 | Establish and maintain information-security policies | docs/architecture.md; docs/security/threat-model.md | Review approved organizational policies and scope | Pending | Organization security owner; repository design is not an approved policy |
| 5.7 | Use relevant threat information | docs/security/threat-model.md | Establish vulnerability/threat-intel review cadence and records | Pending | Security owner; no intel process or scanner configured |
| 5.9 | Maintain an asset inventory | ansible/inventory/hosts.example.yml; docs/network-architecture.md | Reconcile actual central/spoke inventory, owners and service maps | Partial | Platform owner; actual inventory is not provided |
| 5.15 | Define and enforce access control | Ansible WireGuard role; central_base UFW tasks; Nginx auth | Verify deployed SG/UFW/Docker rules and operator access | Partial | Cloud administrator and platform owner; runtime rules unverified |
| 5.16 | Manage identities through lifecycle | Per-host WireGuard keys and metrics/log usernames | Test onboarding, revocation, replacement and offboarding | Partial | Platform owner; rotation/revocation not exercised |
| 5.17 | Protect authentication information | env-backed Ansible secrets; bcrypt htpasswd; protected file modes | Inspect secret handling, access logs and rotation in staging | Partial | Secret custodian; secret store and key custody not formally approved |
| 5.18 | Review and adjust access rights | No Grafana RBAC or periodic access review defined | Configure roles and document access review evidence | Pending | Platform owner and project owners |
| 5.19 | Manage supplier security risks | Versioned upstream container images | Review vendors, image provenance, support and risk acceptance | Pending | Procurement/security owner; supplier review absent |
| 5.24 | Prepare for information-security incidents | docs/security/threat-model.md; docs/operations/ports-capacity-failure-modes.md | Approve incident roles, contacts, severity and playbooks | Partial | Incident response owner; organization procedure not supplied |
| 5.25 | Assess and decide on security events | Prometheus platform alerts; Alertmanager config | Test alert firing/resolution and escalation | Partial | SRE/on-call owner; actual receiver not supplied |
| 5.26 | Respond to information-security incidents | Threat-model acceptance gates and failure-mode guide | Tabletop or controlled incident exercise; record results | Pending | Incident response owner; formal response playbook/exercise absent |
| 5.27 | Learn from incidents | No post-incident review process | Define lessons-learned workflow and evidence | Pending | Incident response owner |
| 5.29 | Maintain security during disruption | Single-node architecture and recovery notes | Review continuity procedures and failover/recovery evidence | Pending | Service owner; hub is a single point of failure |
| 5.30 | Prepare ICT for business continuity | No approved RPO/RTO or restoration test | Approve RPO/RTO; run restore exercise | Pending | Service owner and business continuity owner |
| 5.34 | Protect privacy and personal information | No log sources enabled by starter Alloy config; architecture privacy requirements | Data classification and privacy review for each source/tenant | Partial | Data owner/privacy owner; sources and jurisdictional obligations unknown |
| 5.35 | Independently review security | No independent assessment evidence | Schedule independent SRE/security review and record findings | Pending | Organization security owner |
| 5.37 | Maintain operating procedures | Ansible README and operations failure-mode guide | Review against actual operations; approve and version runbooks | Partial | Platform operations owner; recovery details remain open |
| 6.3 | Provide security awareness | No awareness material/process | Verify organization training records | Pending | HR/security owner |
| 6.8 | Enable reporting of security events | No reporting channel documented | Define contact/channel and test reporting process | Pending | Organization security owner |
| 7.4 | Monitor physical security | AWS provider/host physical controls are outside repository | Obtain cloud-provider assurance and review responsibility model | Pending | Cloud governance owner |
| 8.1 | Secure user endpoint devices | No operator workstation baseline in repository | Review controller endpoint baseline and access protections | Pending | IT/security owner |
| 8.2 | Restrict privileged access | SSH CIDR assertions, Ansible become, gated playbooks | Verify deployed admin accounts, SSH policy and sudo access | Partial | Cloud administrator; actual access roster absent |
| 8.5 | Use secure authentication | Nginx Basic Auth and Grafana anonymous/signup disabled | Test auth, review MFA/RBAC and credential lifecycle | Partial | Platform owner; Grafana MFA/RBAC decision outstanding |
| 8.7 | Protect against malware | Fail2ban and unattended security updates are configured | Review host malware protection and provider controls | Pending | Host/security administrator; no malware detection configured |
| 8.8 | Manage technical vulnerabilities | Versioned image tags and config validation CI | Add image/dependency vulnerability scan and remediation SLA | Pending | Security/SRE owner; scanner and response SLA absent |
| 8.9 | Manage secure configurations | Compose resource/security controls; Ansible roles; CI lint/config checks | Run CI and staging config review; verify drift handling | Partial | Platform owner; runtime drift detection absent |
| 8.10 | Delete information when required | Loki retention 20 days; Prometheus 30-day time target and 3 GB size cap | Measure retention/deletion and validate data lifecycle | Partial | Data owner; actual deletion/retention depends on capacity |
| 8.11 | Mask sensitive information | No log collection sources enabled yet | Implement/test source-specific redaction before onboarding | Pending | Application/data owners; masking patterns not approved |
| 8.12 | Prevent data leakage | No DLP control or data egress review | Define data egress and DLP policy for telemetry | Pending | Security/privacy owner |
| 8.13 | Back up information | No off-host backup implementation | Select target, encryption/key custody, retention, test restore | Pending | Service owner; prerequisites not supplied |
| 8.14 | Provide processing redundancy | Central hub is single-node | Approve and test HA/continuity strategy or formally accept SPOF | Pending | Service owner; no HA configured |
| 8.15 | Log activities | Loki and authenticated push route configured; source collection is not onboarded | Test approved log sources, access and retention | Partial | SRE and data owners; remote sources not selected |
| 8.16 | Monitor systems for anomalies | Prometheus scrape/config/TSDB alerts and dashboard | Run alert simulation and set a real notification receiver | Partial | SRE/on-call owner; coverage and delivery not verified |
| 8.17 | Synchronize clocks | Chrony installed/configured; central timezone Africa/Lagos | Verify NTP synchronization on central and pilot spokes | Partial | Host administrators; no runtime evidence |
| 8.20 | Secure networks | WireGuard, UFW, Nginx TLS and loopback backend bindings in config | Inspect live SG/UFW/Docker rules and tunnel reachability | Partial | Cloud/network administrator; AWS VPC/SG not created |
| 8.22 | Segregate networks | WireGuard peer /32 policy and private Compose bridge | Test no spoke-to-spoke/public backend access | Partial | Network administrator; tests pending |
| 8.24 | Use cryptography appropriately | WireGuard encryption, private CA, TLS 1.2/1.3, CA verification | Review crypto settings, key lifecycle and certificate renewal | Partial | Security owner; rotation and compliance review pending |
| 8.32 | Control changes | Draft PR, CI checks, Ansible obstack_apply gate | Verify approvals, change records and rollback evidence | Partial | Change manager/platform owner; organizational change process not confirmed |

## Evidence and acceptance requirements

For any control to move beyond Partial/Pending, attach objective evidence such as CI run links, reviewed configuration, access-review records, runtime test output, backup restore report, incident exercise notes, supplier assurance or approved risk acceptance. Do not mark controls Implemented solely because a config file exists.

The control owner must confirm applicability, organizational responsibilities, evidence freshness, gaps and risk treatment. This table intentionally does not make an organization-wide compliance claim.