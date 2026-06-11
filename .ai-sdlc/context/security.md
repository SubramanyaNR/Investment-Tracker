# Security Context

Authentication & Isolation:
- Supabase Auth for token issuance.
- ES256 JWT verification in backend.
- Multi-tenancy: Every user-owned table has 'user_id' (NOT NULL).
- RLS policy: 'tenant_isolation' keyed on 'app.current_user_id' GUC.
- Ownership checks return 404 for missing or unauthorized resources.
