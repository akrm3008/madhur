# Business Domain Models

Source: `common-python-utils/src/db/models/business/`

## Organisation (`organisations`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, auto |
| name | String(250) | unique |
| description | String(250) | nullable |
| bbp_platform | String(100) | nullable — bug bounty platform (H1, BC) |
| industry | String(100) | nullable |
| type | Enum(OrganisationType) | default CUSTOMER |
| allowed_email_domains | ARRAY(String(255)) | nullable |
| created_at, updated_at | TIMESTAMP | auto |

Relationships: tlds, asns, members (UserOrgMembership), customer_onboarding

### OrganisationType Enum
CUSTOMER, PROSPECT, BUG_BOUNTY, INTERNAL, DEMO

## TLD (`tlds`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| tld | String(250) | unique |
| organisation_id | Integer | FK → organisations.id |
| tier | Integer | default 2 |
| in_scope | Boolean | default True |
| skip_reason | Enum(SkipReason) | nullable |
| time_skipped | DateTime | nullable |

Relationships: dns_entries, organisation, scans (DomainCollectionScan)

### SkipReason Enum
OUT_OF_SCOPE, TLD_MISSING_FROM_BB_SCOPE, MOVED_PLATFORM, SUSPENDED, LOW_PAYOUTS, BAD_ATTITUDE, TOO_SMALL, REJECT_WILDCARD, NEEDS_VALIDATION, INVALID_DOMAIN, OTHER

## ASN (`org_asns`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| asn | String(50) | unique |
| organisation_id | Integer | FK → organisations.id |
| tier | Integer | default 2 |

Relationships: ips, organisation

## User (`users`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| cognito_sub | String(250) | unique, nullable |

Relationships: user_org_memberships

## UserOrgMembership (`user_org_memberships`)

Base: TimestampedBase (no auto id — composite PK)

| Column | Type | Constraints |
|--------|------|-------------|
| user_id | Integer | PK, FK → users.id |
| organisation_id | Integer | PK, FK → organisations.id |
| role | Enum(UserRoles) | default USER |
| joined_at | TIMESTAMP | auto |
| active | Boolean | default True |
| left_at | TIMESTAMP | nullable |

### UserRoles Enum
USER, OWNER

## UserInvitation (`user_invitations`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| email | String(255) | indexed |
| invitation_token | UUID | unique |
| user_type | Enum(UserType) | default CUSTOMER |
| invited_by_cognito_sub | String(255) | nullable |
| organisation_id | Integer | FK → organisations.id, nullable |
| status | Enum(InvitationStatus) | default PENDING |
| expires_at | TIMESTAMP | default now+7d |
| accepted_at | TIMESTAMP | nullable |

### InvitationStatus Enum
PENDING, ACCEPTED, EXPIRED, REVOKED

### UserType Enum
TRIAL, CUSTOMER

## TrialScan (`trial_scans`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| cognito_sub | String(255) | indexed |
| email | String(255) | indexed |
| domains | ARRAY(Text) | |
| status | Enum(TrialScanStatus) | default PENDING |
| submitted_at | TIMESTAMP | auto |
| processed_at | TIMESTAMP | nullable |
| admin_notes | Text | nullable |
| motivation | Text | nullable |
| domain_collection_flow_id | String(255) | nullable |
| waymore_flow_id | String(255) | nullable |
| content_discovery_flow_id | String(255) | nullable |
| boundary_generation_flow_id | String(255) | nullable |

### TrialScanStatus Enum
PENDING, APPROVED, REJECTED, PROCESSING, COMPLETED

## CustomerOnboarding (`customer_onboarding`)

Base: TimestampedIdBase. Large questionnaire table — see source for full column list. Key columns: `cognito_sub`, `organisation_id`, `completion_status`, `completed_at`.

## AdminImpersonationLog (`admin_impersonation_logs`)

Base: Base (no auto timestamps)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| admin_cognito_sub | String(255) | |
| target_cognito_sub | String(255) | |
| admin_email | String(255) | |
| target_email | String(255) | |
| action | String(50) | |
| ip_address | String(45) | nullable |
| created_at | TIMESTAMP | auto |
