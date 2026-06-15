I have successfully implemented the CSV export feature (**feature-007**) for WealthSignal. 

### Key Deliverables:
1.  **Backend Implementation:**
    *   Created `backend/app/api/export.py` with two new authenticated endpoints: `/export/holdings` and `/export/transactions`.
    *   **Security:** Implemented CSV injection mitigation by prefixing asset names starting with formula-triggering characters (`=`, `+`, `-`, `@`) with a single quote (`'`).
    *   **Performance:** Added `Cache-Control: no-store` to prevent browser caching of sensitive portfolio data and used `StreamingResponse` for efficient data delivery.
    *   **Formatting:** Filenames use **IST** (India Standard Time) and numeric values are plain decimals for direct Excel/Google Sheets compatibility.

2.  **Frontend Integration:**
    *   Added `exportHoldings` and `exportTransactions` helpers to `frontend/lib/api.ts` to handle binary blob downloads.
    *   Introduced a new **"Settings"** tab in the main Dashboard UI (`frontend/app/page.tsx`).
    *   Added a **"Data Export"** section within the Settings tab, featuring dedicated buttons for exporting Holdings and Transaction History with appropriate visual styling and tooltips.
    *   Relocated the **"Sign Out"** button to the new Settings tab for centralized account management (while retaining it in the header for quick access).

3.  **Validation & Testing:**
    *   Developed a comprehensive integration test suite in `backend/tests/integration/test_export.py`.
    *   Verified **401 Unauthorized** responses for both endpoints.
    *   Confirmed **Tenant Isolation**, ensuring users can only export their own data.
    *   Validated **CSV Injection Mitigation** to protect users when opening exports in spreadsheet software.

The feature is now ready for use, allowing investors to backup and analyze their unified portfolio data across crypto, mutual funds, and fixed income assets.