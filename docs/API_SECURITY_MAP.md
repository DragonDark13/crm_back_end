# Backend API Security Map

**Audit scope**
- Backend: `DragonDark13/crm_back_end`, branch `fix/critical-security-issues-2026-11`
- Frontend: `DragonDark13/crm_front_react`, branch `main`
- This document records the routes declared in the backend source and frontend calls found in the API modules/components.
- No application code or frontend code was changed as part of this audit.
- Role assignments below are recommendations, not existing enforcement.

## 1. Authentication status legend

| Status | Meaning |
|---|---|
| Public | No authentication decorator / credential check on this route |
| JWT | Route has `@jwt_required()` |
| Webhook secret | Requires `X-Webhook-Secret` matching `WEBHOOK_SECRET`; not a user JWT |
| No role check | No role authorization decorator/check found |

The backend currently defines `guest` and `manager` roles and creates users from environment variables. This does not mean routes enforce those roles.

## 2. Complete route inventory

All paths below include the `/api` prefix added in `app.py`, except `/update_server`.

### 2.1 Authentication and system

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| POST | `/api/login` | `app.py::login` | Public; username/password | None | Verify credentials and issue JWT | `POST /login` |
| POST | `/api/logout` | `app.py::logout` | JWT | None | Returns success; does not revoke token server-side | `POST /logout` with Bearer token in `_user.ts`; currently the main App logout flow clears local state directly |
| GET | `/api/protected` | `app.py::protected` | JWT | None | Token check / current identity | No call found |
| POST | `/update_server` | `app.py::webhook` | Webhook secret header | Not applicable | Executes git fetch/pull for deployment | No call found; external webhook expected |

### 2.2 Products and inventory

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/product/{product_id}` | `app.py::get_product` | Public | None | Fetch one product | No direct GET call found; same URL is used for PUT/DELETE |
| POST | `/api/add_new_product` | `app.py::create_and_purchase_product` | Public | None | Create product and initial purchase | `POST /add_new_product` |
| GET | `/api/get_all_products/` | `api/products_api.py::ProductList.get` | Public | None | List products | `GET /get_all_products` |
| PUT | `/api/product/{product_id}` | `services/product_service.py::update_product` | Public | None | Update product | `PUT /product/{id}` |
| DELETE | `/api/product/{product_id}` | `services/product_service.py::delete_product` | Public | None | Delete one product | `DELETE /product/{id}` |
| DELETE | `/api/delete_all_products` | `services/product_service.py::delete_all_products` | Public | None | Delete all products and related records | `DELETE /delete_all_products` |
| POST | `/api/product/{product_id}/inventory` | `services/product_service.py::inventory_product` | JWT | None | Inventory reconciliation | `POST /product/{id}/inventory`; frontend manually adds Bearer token |
| GET | `/api/product/{product_id}/history` | `services/product_service.py::get_product_history` | Public | None | Product stock/purchase/sale history | `GET /product/{id}/history` |
| POST | `/api/product/{product_id}/purchase` | `services/product_service.py::purchase_product` | Public | None | Record purchase / increase stock | `POST /product/{id}/purchase` |
| POST | `/api/product/{product_id}/sale` | `services/product_service.py::record_sale` | Public | None | Record sale / decrease stock | `POST /product/{id}/sale` |
| DELETE | `/api/delete-history/{product_id}/{history_type}/{history_id}` | `services/product_service.py::delete_product_history` | Public | None | Delete a selected history record (stock, purchase, or sale depending on type) | `DELETE /delete-history/{productId}/{historyType}/{historyId}` |

### 2.3 Categories

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/categories/get_all_categories` | `services/category_routes.py::CategoryList.get` | Public | None | List categories | `GET /categories/get_all_categories` |
| POST | `/api/add_new_category` | `services/category_routes.py::create_category` | Public | None | Create category | `POST /add_new_category` |
| GET | `/api/product/{product_id}/categories` | `services/category_routes.py::get_product_categories` | Public | None | Read product categories | No direct call found in API modules |
| POST | `/api/product/{product_id}/categories` | `services/category_routes.py::assign_categories_to_product` | Public | None | Assign categories to product | No direct call found in API modules |

### 2.4 Customers

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| POST | `/api/customer_create` | `services/customer_routes.py::create_customer` | Public | None | Create customer | `POST /customer_create` |
| GET | `/api/customers/get_all_customers` | `services/customer_routes.py::CustomerList.get` | Public | None | List customers | `GET /customers/get_all_customers` |
| GET | `/api/customers_details/{customer_id}` | `services/customer_routes.py::get_customer_details` | Public | None | Customer details and associated sales | `GET /customers_details/{id}` |
| PUT | `/api/update_customers/{customer_id}` | `services/customer_routes.py::edit_customer` | Public | None | Update customer | `PUT /update_customers/{id}` |
| DELETE | `/api/delete_customers/{customer_id}` | `services/customer_routes.py::delete_customer_route` | Public | None | Delete customer | `DELETE /delete_customers/{id}` |

### 2.5 Product suppliers

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| POST | `/api/create_supplier` | `services/supplier_routes.py::create_supplier` | Public | None | Create product supplier | `POST /create_supplier` |
| GET | `/api/suppliers/get_suppliers_list` | `services/supplier_routes.py::SupplierList.get` | Public | None | List product and packaging suppliers | `GET /suppliers/get_suppliers_list` |
| GET | `/api/supplier/{supplier_id}/purchase-history` | `services/supplier_routes.py::get_supplier_purchase_history_api` | Public | None | Supplier purchase history | `GET /supplier/{id}/purchase-history` |
| GET | `/api/supplier/{supplier_id}/products` | `services/supplier_routes.py::get_supplier_products_api` | Public | None | Products belonging to supplier | `GET /supplier/{id}/products` |
| DELETE | `/api/delete_supplier/{supplier_id}` | `services/supplier_routes.py::delete_supplier` | Public | None | Delete supplier | `DELETE /delete_supplier/{id}` |
| PUT | `/api/supplier_edit/{supplier_id}` | `services/supplier_routes.py::update_supplier` | Public | None | Update supplier | `PUT /supplier_edit/{id}` |

### 2.6 Packaging materials and packaging suppliers

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/packaging/get_all_packaging_materials` | `services/package_services.py::PackagingMaterialList.get` | Public | None | List packaging materials | `GET /packaging/get_all_packaging_materials` |
| GET | `/api/get_all_packaging_suppliers` | `services/package_services.py::get_all_suppliers` | Public | None | List packaging suppliers | `GET /get_all_packaging_suppliers` |
| POST | `/api/add_new_packaging_suppliers` | `services/package_services.py::add_supplier` | Public | None | Create packaging supplier | `POST /add_new_packaging_suppliers` |
| POST | `/api/purchase_current_packaging` | `services/package_services.py::purchase_current_packaging_material` | Public | None | Purchase packaging material | `POST /purchase_current_packaging` |
| POST | `/api/update_packaging_status` | `services/package_services.py::update_packaging_status` | Public | None | Mark packaging as used / update stock status | `POST /update_packaging_status` |
| OPTIONS | `/api/update_packaging_status` | Flask automatic/CORS preflight and route's declared methods | Public | Not applicable | Preflight request | Browser may send automatically |
| GET | `/api/materials/{packaging_material_id}/history` | `services/package_services.py::get_packaging_material_history` | Public | None | Packaging material history | `GET /materials/{id}/history` |
| DELETE | `/api/delete_all_materials` | `services/package_services.py::delete_all_packaging_materials` | Public | None | Delete all packaging materials | `DELETE /delete_all_materials` |
| GET | `/api/packaging-supplier/{supplier_id}/purchase-history` | `services/package_services.py::get_packaging_supplier_purchase_history_api` | Public | None | Packaging supplier purchase history | `GET /packaging-supplier/{id}/purchase-history` |
| PUT | `/api/packaging_supplier_edit/{supplier_id}` | `services/package_services.py::update_packaging_supplier` | Public | None | Update packaging supplier | `PUT /packaging_supplier_edit/{id}` |
| DELETE | `/api/delete_packaging_supplier/{supplier_id}` | `services/package_services.py::delete_packaging_supplier` | Public | None | Delete packaging supplier | `DELETE /delete_packaging_supplier/{id}` |

### 2.7 Gift sets

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| POST | `/api/create_gift_set` | `services/gift_box_services.py::create_gift_set` | Public | None | Create gift set | `POST /create_gift_set` |
| GET | `/api/gift_set_show_details/{gift_set_id}` | `services/gift_box_services.py::get_gift_set` | Public | None | Gift set details | No direct call found in API wrapper |
| PUT | `/api/update_gift_set/{gift_set_id}` | `services/gift_box_services.py::update_gift_set` | Public | None | Update gift set | `PUT /update_gift_set/{id}` |
| DELETE | `/api/remove_gift_set/{gift_set_id}` | `services/gift_box_services.py::dismantle_gift_set` | Public | None | Remove/dismantle gift set | `DELETE /remove_gift_set/{id}` |
| POST | `/api/sell_gift_set/{gift_set_id}` | `services/gift_box_services.py::sell_gift_set` | Public | None | Sell gift set | `POST /sell_gift_set/{id}` |
| GET | `/api/get_all_gift_sets` | `services/gift_box_services.py::get_gift_sets` | Public | None | List gift sets | `GET /get_all_gift_sets` |
| GET | `/api/get_all_gift_set_sales_history` | `services/gift_box_services.py::get_gift_set_sales_history` | Public | None | Gift set sales history | Search by exact path did not return a direct hit in API modules; inspect component-level usage before changing |

### 2.8 Purchase and sales history

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/get_all_purchase_history` | `services/purchase_history_bp.py::get_purchase_history_data` | Public | None | Combined purchase history | `GET /get_all_purchase_history` |
| GET | `/api/get_all_sales_history` | `services/sales_history_services.py::get_sales_history` | Public | None | Combined sales history | `GET /get_all_sales_history` |

**Important:** `delete_all_purchase_history()` exists in `services/purchase_history_bp.py`, but has no Flask route decorator. It is not an HTTP endpoint in the inspected source. Do not add it to route protection as if it were currently exposed.

### 2.9 Other investments

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/investments/get_all_investments` | `services/other_investments_services.py::InvestmentList.get` | Public | None | List investments | `GET /investments/get_all_investments` |
| POST | `/api/create_new_investments` | `services/other_investments_services.py::add_investment` | Public | None | Create investment | `POST /create_new_investments` |
| DELETE | `/api/delete_investments/{investments_id}` | `services/other_investments_services.py::delete_investment` | Public | None | Delete one investment | `DELETE /delete_investments/{id}` |
| DELETE | `/api/delete_all_investments` | `services/other_investments_services.py::delete_all_investments` | Public | None | Delete all investments | `DELETE /delete_all_investments` |

### 2.10 Statistics

All routes below are registered with blueprint prefix `/api/statistics`.

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| GET | `/api/statistics/sales/monthly` | `services/statistics_services.py::get_monthly_sales_statistics` | Public | None | Monthly sales totals, quantity, profit | `GET /statistics/sales/monthly` |
| GET | `/api/statistics/purchases/monthly` | `services/statistics_services.py::get_monthly_purchases_statistics` | Public | None | Monthly purchase totals, quantity, average price | `GET /statistics/purchases/monthly` |
| GET | `/api/statistics/stock` | `services/statistics_services.py::get_stock_levels` | Public | None | Product stock levels | `GET /statistics/stock` |
| GET | `/api/statistics/profit-expense` | `services/statistics_services.py::get_profit_expense_by_month` | Public | None | Monthly sales/profit/expenses | No direct call found in inspected Dashboard excerpt |
| GET | `/api/statistics/customer-activity` | `services/statistics_services.py::get_customer_activity` | Public | None | Active customers by day | No direct call found in inspected Dashboard excerpt |
| GET | `/api/statistics/top-products` | `services/statistics_services.py::get_top_10_products` | Public | None | Top ten products by sales quantity | `GET /statistics/top-products` |

### 2.11 Excel export

| Method | Endpoint | Backend source / handler | Current authentication | Role enforcement | Operation | Frontend use |
|---|---|---|---|---|---|---|
| POST | `/api/export-products-excel` | `services/export_to_excel_services.py::export_products` | Public | None | Export selected product data to XLSX | `POST /export-products-excel` with `product_ids`; response treated as blob |

## 3. Frontend authentication integration findings

Inspected frontend files:
- `src/api/api.ts`
- `src/api/_user.ts`
- `src/api/_product.ts`
- `src/components/context/AuthContext.tsx`
- `src/components/ProtectedRoute/ProtectedRoute.tsx`
- `src/App.tsx`

Findings:

1. Axios instance has no request interceptor that attaches the JWT to ordinary API calls.
2. The token is stored in `localStorage` by `AuthContext`.
3. Explicit Bearer headers are currently added only for inventory and logout calls in the inspected API modules.
4. `ProtectedRoute` checks only whether a token string exists in local storage/context. It does not validate the token with backend and does not inspect roles.
5. In `App.tsx`, only the dashboard route is wrapped in `ProtectedRoute`. Products, gift sets, clients, sales, purchases, analytics, packaging, investments and suppliers routes are not wrapped there.
6. The main App logout handler calls context `logout()`, which removes the local token; it does not call backend `/logout`. The separate `logoutUser()` helper does call backend but prints the token to console.
7. No role-aware frontend gating was found in the inspected auth context / route guard.
8. As a result, simply adding JWT protection to backend routes will break current frontend requests unless the frontend starts sending the token on those requests (or a deliberately public subset is retained).

## 4. Frontend/backend path discrepancy

The API constant `API_ENDPOINTS.ADD_NEW_PACKAGING_MATERIAL` in `src/api/api.ts` is `/packaging_materials/purchase`, but the corresponding backend route is commented out in `services/package_services.py`. The active backend endpoint is `POST /api/purchase_current_packaging`, and the active UI component `PurchaseMaterialDialog.tsx` calls that endpoint directly.

This appears to be a stale/unused API constant rather than a current broken UI call, but verify usages before removing or changing it.

## 5. Recommended access policy (proposal only)

These are recommendations for a later implementation stage. They are not applied in this audit.

| Operation group | Guest | Manager | Notes |
|---|---|---|---|
| Login | Public | Public | Required to obtain JWT |
| Read product catalog, categories, suppliers, packaging catalog | Allow | Allow | Confirm whether guest should see commercial data |
| Read customers and customer details | Deny or restrict | Allow | Contains customer contact details and linked sales |
| Read sales/purchase histories and financial statistics | Deny or restrict | Allow | Contains sensitive business information |
| Read stock and operational lists | Allow | Allow | Confirm business requirements |
| Create/update products, categories, customers, suppliers, packaging, gift sets, investments | Deny | Allow | Mutating operations |
| Sales, purchases, packaging consumption, gift set sale | Deny | Allow | Financial and stock mutations |
| Inventory | Deny | Allow | Currently JWT-only; add role check |
| Delete one record / delete history | Deny | Manager only with explicit safeguards | Consider separate elevated role for destructive history operations |
| Bulk delete | Deny | Deny by default | Prefer a separate admin-only workflow with confirmation, audit log and backup |
| Excel export | Deny or restrict | Allow | Export exposes stock and pricing data |
| Deployment webhook | Not applicable | Not applicable | Keep separate secret-based authentication; rotate secret and constrain deployment behavior |

## 6. Implementation hazards to address before applying route guards

1. Add a shared Axios request interceptor (or equivalent central token injection) before protecting endpoints used by frontend. Do not duplicate token handling endpoint-by-endpoint.
2. Decide whether all application pages require login. Current UI routes are mostly not protected even though the dashboard is.
3. Define whether guest can access customers, supplier purchase histories, sales/purchase histories, and financial analytics. These are not equivalent to public catalog reads.
4. Add role checks on backend; hiding buttons or pages in React is not authorization.
5. Keep OPTIONS/CORS preflight working. Do not require JWT for browser preflight requests.
6. The logout endpoint currently does not revoke tokens. Client-side token removal is not server-side token invalidation.
7. The webhook is not a normal user route. Keep its secret check separate from JWT/role decorators.
8. Protect bulk deletion and history deletion more strictly than ordinary CRUD.
9. Do not change business logic or response shapes as part of the authorization patch.
10. Verify exact deployed route behavior and trailing-slash handling with integration tests after implementation.

## 7. Audit completeness and limitations

- The route inventory above is based on route decorators, blueprint registrations and RESTX namespace registrations in the inspected branch.
- Helper functions without route decorators are not listed as HTTP endpoints.
- The frontend mapping is based on API wrapper files and code-search matches in the inspected `main` branch. A few routes may be called directly from components or dynamically; those should be checked during implementation.
- No live requests, automated tests, or runtime route enumeration were performed.
- No backend/frontend source code was modified by this audit.