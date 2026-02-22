# Logistics Decision Support System (DSS)
# Project Requirements Summary

**Project Name:** Logistics DSS
**Version:** 1.0
**Date:** 2026-02-12
**Author:** Gilvan de Azevedo

---

## 1. Business Context

| Aspect | Specification |
|--------|---------------|
| **Industry** | Distribution/Wholesale |
| **Scale** | Variable (adaptable to different client sizes) |
| **Users** | Inventory Managers (operational) + Executives (strategic) |
| **Delivery** | Desktop Application (offline capable) |
| **Languages** | Trilingual (English, Portuguese, Spanish) |

---

## 2. Data & Integration

| Aspect | Specification |
|--------|---------------|
| **Data Source** | Full ERP data (sales, stock, suppliers, lead times, costs) |
| **Import Methods** | CSV/Excel upload, Database connection, API integration |

---

## 3. Core Decisions Supported

1. **When to Reorder** - Optimal reorder points and timing
2. **How Much to Order** - Economic order quantities (EOQ)
3. **Where to Allocate** - Distribution across locations/channels

---

## 4. Dashboard KPIs

| Category | Metrics |
|----------|---------|
| **Stock Health** | Current levels, days of supply, turnover rates |
| **Service Level** | Fill rates, stockout frequency, backorders |
| **Financial** | Carrying costs, ordering costs, total inventory value |

---

## 5. AI-Powered Features

| Feature | Description |
|---------|-------------|
| **Demand Forecasting** | Predict future demand using historical patterns |
| **Reorder Alerts** | Smart notifications for replenishment needs |
| **ABC/XYZ Classification** | Auto-categorize by value and demand variability |

---

## 6. Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Application                       │
│                  (Python + CustomTkinter)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Operational │  │  Executive  │  │  Settings/Config    │ │
│  │    View     │  │    View     │  │  (Language, Data)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Analytics Engine                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│  │   Demand     │ │   Inventory  │ │   ABC/XYZ           ││
│  │  Forecasting │ │ Optimization │ │   Classification    ││
│  └──────────────┘ └──────────────┘ └──────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  CSV/    │  │ Database │  │   API    │  │  Local   │   │
│  │  Excel   │  │ Connector│  │  Client  │  │  SQLite  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Development Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| **1** | Core Data Layer | CSV/Excel import, local database, data validation |
| **2** | Basic Dashboard | Stock levels, KPI display, operational view |
| **3** | Analytics Engine | ABC classification, turnover calculations |
| **4** | Forecasting | Demand prediction using historical data |
| **5** | Optimization | Reorder points, EOQ, alerts |
| **6** | Executive View | Strategic dashboards, reports |
| **7** | Multi-language | i18n support (EN/PT/ES) |
| **8** | Advanced Integration | Database connectors, API support |

---

## 8. Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.12 | Modern, extensive libraries, cross-platform |
| **Desktop UI** | CustomTkinter | Modern appearance, native feel |
| **Database** | SQLite | Embedded, no installation required |
| **Analytics** | Pandas, NumPy | Industry standard for data manipulation |
| **Forecasting** | Statsmodels, Prophet | Proven demand forecasting libraries |
| **Charts** | Matplotlib, Plotly | Rich, interactive visualizations |
| **Packaging** | PyInstaller | Create standalone executables |

---

## 9. User Roles & Views

### 9.1 Operational View (Inventory Managers)
- Real-time stock levels by SKU and location
- Reorder alerts and recommendations
- Daily/weekly operational KPIs
- Item-level drill-down capabilities

### 9.2 Executive View (Directors)
- High-level KPI dashboards
- Trend analysis and forecasts
- Financial impact summaries
- Strategic inventory health indicators

---

## 10. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| **Performance** | Handle 10,000+ SKUs without lag |
| **Offline** | Full functionality without internet |
| **Portability** | Single executable, no installation dependencies |
| **Data Security** | Local storage, no cloud transmission |
| **Usability** | Intuitive interface, minimal training required |

---

## 11. Success Criteria

1. Managers can identify reorder needs in < 30 seconds
2. System accurately forecasts demand with < 15% MAPE
3. ABC/XYZ classification runs automatically on data import
4. Executives can view strategic KPIs in a single dashboard
5. Application runs on Windows, macOS, and Linux

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-12 | Initial requirements gathering |
