import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const read = path => readFileSync(path, 'utf8');

assert.equal(existsSync('site-v2/finance-gate-sitewide.js'), true, 'Canonical VPBank sitewide runtime must exist');
assert.equal(existsSync('scripts/sitewide_product_surface.py'), true, 'Canonical Shopee four-card builder must exist');

const conversion = read('scripts/apply_conversion_v2.py');
assert.match(conversion, /checkout-enhance\.js/);
assert.match(conversion, /finance-banner\.js/);
assert.match(conversion, /affiliate-visibility\.js/);

const primaryAffiliate = read('site-v2/affiliate-visibility.js');
assert.match(primaryAffiliate, /Gợi ý số ngày hôm nay/);
assert.match(primaryAffiliate, /dailyRecommendationHeading/);
assert.match(primaryAffiliate, /reportDateLabel/);
assert.doesNotMatch(primaryAffiliate, /function\s+installStrip/);
assert.doesNotMatch(primaryAffiliate, /data-primary-affiliate-strip/);
assert.doesNotMatch(primaryAffiliate, /https?:\/\/(?:nguyenlinhtkv|go\.isclix)/i);
assert.doesNotMatch(primaryAffiliate, /position\s*:\s*fixed/i);
assert.doesNotMatch(primaryAffiliate, /effectivecpmnetwork|highperformanceformat|adsterra/i);

const restore = read('site-v2/affiliate-restore.js');
assert.match(restore, /Retired runtime/);
assert.doesNotMatch(restore, /function\s+ensureEarlyStrip/);
assert.doesNotMatch(restore, /SHOPEE_URL/);
assert.doesNotMatch(restore, /data-primary-affiliate-strip/);
assert.doesNotMatch(restore, /effectivecpmnetwork|highperformanceformat|adsterra/i);

const commerce = read('site-v2/finance-banner.js');
assert.match(commerce, /MỞ BẢN PHÂN TÍCH AI/);
assert.match(commerce, /30\.000đ/);
assert.match(commerce, /15\.000 lượt tính toán AI/);
assert.match(commerce, /ai_checkout_intent/);
assert.match(commerce, /ai_checkout_open/);
assert.match(commerce, /ai_payment_qr_view/);
assert.match(commerce, /ai_payment_claim_submit/);
assert.match(commerce, /ai_purchase_window_closed/);
assert.match(commerce, /SALE_CUTOFF_MINUTES = 18 \* 60/);
assert.match(commerce, /lemienbac_email_order_v1/);
assert.match(commerce, /order\.status === "pending" \|\| order\.status === "approved"/);
assert.match(commerce, /reportDate !== now\.date/);
assert.match(commerce, /stale_report/);
assert.match(commerce, /closeCheckoutForGate/);
assert.match(commerce, /phân tích, thống kê và soi cầu/i);
assert.doesNotMatch(commerce, /function\s+installAffiliateFallback/);
assert.doesNotMatch(commerce, /affiliate-shopee-smartlink/);
assert.doesNotMatch(commerce, /https?:\/\/(?:nguyenlinhtkv|go\.isclix)/i);
assert.doesNotMatch(commerce, /Khi cần phần kết luận riêng cho ngày/);

const checkoutEntry = read('site-v2/checkout-entry.js');
assert.match(checkoutEntry, /Fail closed/);
assert.match(checkoutEntry, /!button/);
assert.doesNotMatch(checkoutEntry, /checkout\.hidden\s*=\s*false/);
assert.doesNotMatch(checkoutEntry, /classList\.add\("modal-open",\s*"checkout-open"\)/);

const checkout = read('site-v2/checkout-enhance.js');
assert.match(checkout, /VietQR/);
assert.match(checkout, /ACCOUNT_HOLDER/);
assert.match(checkout, /AMOUNT = 30000/);
assert.doesNotMatch(checkout, /function\s+addDirectShopeeDeals/);
assert.doesNotMatch(checkout, /function\s+setupShopeeNudge/);
assert.doesNotMatch(checkout, /go\.isclix\.com/i);

const surface = read('scripts/sitewide_product_surface.py');
assert.match(surface, /class=\"lm-shop-grid\"/);
assert.match(surface, /class=\"lm-shop-item\"/);
assert.match(surface, /data-sitewide-products=\"true\"/);
assert.match(surface, /data-affiliate-static-placement=\"after_tools\"/);
assert.match(surface, /\/go\/shopee\/\?p=/);
assert.match(surface, /affiliate_product_grid_view/);
assert.match(surface, /affiliate_product_click/);
assert.match(surface, /display:block!important;visibility:visible!important;opacity:1!important/);
assert.match(surface, /finance-gate-sitewide\.js/);
assert.match(surface, /finance-gate\\\.js/);

const finance = read('site-v2/finance-gate-sitewide.js');
assert.match(finance, /MIN_DELAY_MS = 3000/);
assert.match(finance, /MIN_SCROLL_RATIO = 0\.08/);
assert.match(finance, /lm_vpbank_banner_closed_v3/);
assert.match(finance, /early_finance_banner_sitewide_v3/);
assert.match(finance, /lm-sponsor-vp/);
assert.match(finance, /Vay tiền online/);
assert.match(finance, /Đóng quảng cáo/);
assert.match(finance, /data-go-vpbank/);
assert.match(finance, /affiliate_finance_view/);
assert.match(finance, /affiliate_finance_click/);
assert.match(finance, /affiliate_finance_close/);
assert.match(finance, /closeOffer\("checkout_open", false\)/);
assert.match(finance, /closeOffer\("checkout_intent", false\)/);
assert.doesNotMatch(finance, /COOLDOWN_MS/);
assert.doesNotMatch(finance, /24h/);
assert.doesNotMatch(finance, /href=\"https:\/\/go\.isclix\.com/i);

const affiliateConfig = JSON.parse(read('data/affiliate-offers.json'));
assert.equal(affiliateConfig.enabled, true, 'ACCESSTRADE canonical state must be enabled');
assert.equal(affiliateConfig.network, 'ACCESSTRADE');
assert.equal(affiliateConfig.policy?.adsterra_display, false);
assert.equal(affiliateConfig.policy?.shopee_single_canonical_surface, true);
const retiredStrip = affiliateConfig.placements?.find(item => item.id === 'shopee-early-strip');
assert.equal(retiredStrip?.enabled, false, 'Legacy Shopee early strip must remain retired');
const productGrid = affiliateConfig.placements?.find(item => item.id === 'shopee-product-grid');
assert.equal(productGrid?.enabled, true, 'Canonical Shopee product grid must stay enabled');
assert.equal(productGrid?.product_count, 4, 'Canonical Shopee grid must contain four products');
const vpbank = affiliateConfig.placements?.find(item => item.id === 'vpbank-vay-online');
assert.equal(vpbank?.enabled, true, 'VPBank sitewide placement must stay enabled');
assert.equal(vpbank?.delay_ms, 3000);
assert.equal(vpbank?.min_scroll_ratio, 0.08);
assert.equal(vpbank?.cooldown_hours, 0);

const homeBuilder = read('scripts/apply_home_portal_safe.py');
assert.match(homeBuilder, /data-ai-commerce-trust/);
assert.match(homeBuilder, /data-ai-product-proof/);
assert.match(homeBuilder, /data-ai-sticky-cta/);
assert.match(homeBuilder, /mô tả lịch sử, không phải xác suất hay cam kết/i);

console.log('CANONICAL_AI_AFFILIATE_COMMERCE_POLICY_OK');
