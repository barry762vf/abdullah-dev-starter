# Project purpose

Abdullah Developer Kit is a reusable, production-oriented foundation for web applications, not a finished business product. It can be cloned for freelance work, SaaS, business systems, academic projects, internal tools and AI-enabled products.

The baseline provides authentication, database-backed roles, administration, bilingual Arabic/English presentation, explicit migrations, tests, and two same-origin deployment paths. The `.ai/` files preserve decisions and engineer handoffs. A clone should change its name, branding, domain, data model and authorization rules for its users; see [customization](CUSTOMIZATION.md).

Only Gemini, Telegram, Supabase Storage and SMTP have reference adapters. They are disabled by default and require credentials and project-specific policy before use. OpenAI, WhatsApp, S3, payment processing, content management, teacher/student roles and product-specific dashboards are examples a clone could build, not shipped features.

Design priorities are readable code, explicit security boundaries, Arabic RTL/English LTR parity, verifiable database behavior and deployable defaults. The development roadmap is complete through Phase 8; the next work is release and deployment verification, not another foundation phase.
