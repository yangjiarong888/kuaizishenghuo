# Mall business read-only decomposition review

## Result

The strict navigation-only verification completed successfully on the connected Android device. It searched for `可乐`, opened and captured a product-detail page, returned safely, and closed its Appium driver. No business-data mutation action was executed.

## Delivered commits

| Commit | Changed files |
| --- | --- |
| `26eab9a refactor: extract mall business search` | `pages/shop_business_page.py`, `pages/shop_business_search_mixin.py`, `testcases/test_shop_business_decomposition.py` |
| `0d999ac refactor: extract mall business detail` | `pages/shop_business_page.py`, `pages/shop_business_detail_mixin.py`, `testcases/test_shop_business_decomposition.py` |
| `3832619 fix: fail closed in mall navigation verification` | `pages/shop_home_page.py`, `scripts/run_mall_order_flow.py`, `testcases/test_mall_order_safety.py`, `testcases/test_shop_home_navigation.py` |
| `a63e281 fix: guard mall structural fallback` | `pages/shop_home_page.py`, `testcases/test_shop_home_navigation.py` |

The last two commits are approved safety fixes discovered during the initial read-only attempt. In strict navigation mode, they disable both direct mall-tab coordinate fallback and the structural-click failure `mobile: clickGesture` fallback; the flag is restored in `finally`. Default flows retain their historical fallback behavior.

## Static and offline verification

| Check | Result |
| --- | --- |
| `ShopBusinessPage` facade size | 1,322 lines before extraction at `4bb07d4`; 484 lines after |
| Mall-focused pytest set | 139 passed |
| Full non-device pytest | 273 passed, 1 deselected |
| In-memory compilation | `compiled=96` |
| Combined fixed waits in facade/search/detail files | 52 (baseline cap: 52) |
| Combined broad-exception handlers in facade/search/detail files | 47 (baseline cap: 47) |

The focused command included every `testcases/test_mall_order_*.py` file plus `test_shop_home_navigation.py` and `test_shop_business_decomposition.py`. Compilation enumerated every non-`__pycache__` Python file from the worktree and decoded BOM-bearing sources with `utf-8-sig`.

## Device run

| Field | Evidence |
| --- | --- |
| Device | `P7T4XC99CYAEYL4H`, model `21091116AC` (`evergo`), state `device` |
| Pre-run settings (read only) | `airplane_mode_on=1`; `wifi_on=2` |
| Appium | `127.0.0.1:4723`, ready, version `3.2.0` |
| Command | `C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe scripts\run_mall_order_flow.py --verify-navigation-only --product-source search --keyword "可乐" --session mall_readonly_decomposition_verify --start-mode activate --quit-driver` |
| Exit code / duration | `0` / `150.854` seconds |
| Driver lifecycle | Created successfully and closed normally for session `mall_readonly_decomposition_verify` |
| Post-run activity | `com.bs.feifubao/.activity.MainActivity` |

## Evidence review

- Screenshot: `logs/20260728_145117_683760_mall_navigation_verification.png` — visually inspected; it shows `可口可乐(经典美味)330ml` on the product-detail page.
- Sanitized XML: `logs/20260728_145117_683760_mall_navigation_verification.xml` — corresponding detail-page hierarchy exists; 54 `<redacted>` values were present and the sensitive phone/code/password-like attribute scan found zero non-redacted literal values.
- Run log: `logs/chopsticklife_20260728_144928.log` — records semantic/structural mall-tab navigation, search entry, keyword input, search confirmation, product-detail snapshot, two safe back navigations, and normal driver close.

## Zero-mutation conclusion

**Zero business-data mutation is verified for this run.** The exact command supplied no mutation capability or business-action flag. The reviewed log contains no executed add-cart, share/copy, IM, checkout, submit-order, payment, address mutation, cancellation, stockout, or network-exception action. The screenshot contains add-cart and buy-now controls as passive detail-page UI only; the run log records neither control being clicked. This conclusion is limited to the navigation-only path.

## Excluded device coverage

This device evidence does not claim compatibility for cart, share/copy-link, IM, checkout, order creation, payment, address creation/edit/copy, cancellation, stockout, or network-exception flows. Those actions were neither authorized nor run.

## Recommended next governance batch

The combined fixed-wait and broad-exception counts are exactly at their allowed ceilings (52 and 47). The next focused maintenance batch should replace the most expensive search/detail fixed sleeps with state-based waits and split the highest-risk broad exception handlers into expected Appium lookup/click failures versus unexpected driver errors, while preserving the current strict-navigation safety tests.
