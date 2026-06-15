## Modified Files (git diff HEAD)

```diff
diff --git a/backend/app/main.py b/backend/app/main.py
index fc0ff8d..0b5485a 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,7 +1,8 @@
 import time
 import uuid
+from contextlib import asynccontextmanager
 
 from fastapi import Depends, FastAPI, Request
 from fastapi.middleware.cors import CORSMiddleware
 from fastapi.responses import JSONResponse
 from app.api.dashboard import router as dashboard_router
@@ -21,11 +22,20 @@ from app.api.account import router as account_router
 from app.api.importer import router as importer_router, public_router as importer_public_router
 from app.api.xirr import router as xirr_router
 from app.api.performance import router as performance_router
 from app.api.export import router as export_router
 
-app = FastAPI(title="Investment Observability API")
+
+@asynccontextmanager
+async def lifespan(app: FastAPI):
+    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
+    if settings.scheduler_enabled:
+        start_scheduler()
+    yield
+
+
+app = FastAPI(title="Investment Observability API", lifespan=lifespan)
 
 
 app.add_middleware(
     CORSMiddleware,
     allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
@@ -58,17 +68,10 @@ async def log_unhandled(request: Request, exc: Exception):
         type=type(exc).__name__, msg=redact(str(exc)),
     )
     return JSONResponse(status_code=500, content={"detail": "Internal server error"})
 
 
-@app.on_event("startup")
-async def startup():
-    # Schema is managed by Alembic — run `alembic upgrade head` on deploy, not here.
-    if settings.scheduler_enabled:
-        start_scheduler()
-
-
 @app.get("/health")
 async def health():
     return {"status": "ok"}
```
