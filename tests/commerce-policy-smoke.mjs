import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const read = path => readFileSync(path, 'utf8');

assert.equal(
  existsSync('site-v2/finance-gate.js'),
  true,
  'Secondary finance affiliate source must exist'
);
assert.equal(
  existsSync('site-v2/affiliate-visibility.js'),
  true,
  'Visible AI-safe affiliate strip source must exist'
);

const conversion = read('scripts/apply_conversion_v2.py');
assert.match(conversion, /finance-gate\.js/);
assert.match(conversion, /FINANCE_GATE_SCRIPT_TAG/);
assert.match(conversion, /finance-banner\.js/);
assert.match(conversion, /affiliate-visibility\.js/);
assert.match(conversion, /AFFILIATE_VISIBILITY_SCRIPT_TAG/);

const primaryAffiliate = read('site-v2/affiliate-visibility.js');
assert.match(primaryAffiliate, /after_tools_visible/);
assert.match(primaryAffiliate, /affiliate_shopee_strip_view/);
assert.match(primaryAffiliate, /affiliate_shopee_strip_click/);
assert.match(primaryAffiliate, /lemienbac_purchase_/);
assert.match(primaryAffiliate, /lm_ai_purchase_intent_v1/);
assert.match(primaryAffiliate, /lm_affiliate_intent_v1/);
assert.match(primaryAffiliate, /primaryAffiliateStrip|data-primary-affiliate-strip/);
assert.match(primaryAffiliate, /data-open-checkout/);
assert.match(primaryAffiliate, /data-ai-sticky-cta/);
assert.doesNotMatch(primaryAffiliate, /position\s*:\s*fixed/i);
assert.doesNotMatch(primaryAffiliate, /effectivecpmnetwork|highperformanceformat|adsterra/i);

const commerce = read('site-v2/finance-banner.js');
assert.match(commerce, /affiliate-shopee-smartlink/);
assert.match(commerce, /MỞ BẢN PHÂN TÍCH AI/);
assert.match(commerce, /30\.000đ/);
assert.match(commerce, /\.lm-product-deals/);
assert.match(commerce, /\.lm-shopee-nudge\{display:none!important\}/);
assert.match(commerce, /after_proof/);
assert.match(commerce, /affiliate_product_grid_view/);
assert.match(commerce, /ai_checkout_intent/);
assert.match(commerce, /ai_checkout_open/);
assert.match(commerce, /ai_payment_qr_view/);
assert.match(commerce, /ai_payment_claim_submit/);

const checkout = read('site-v2/checkout-enhance.js');
assert.match(checkout, /affiliate_product_click/);
assert.match(checkout, /Tông đơ Philips MG3911\/15 7in1/);
assert.match(checkout, /Sạc dự phòng Anker Zolo 20\.000mAh 22\.5W/);
assert.match(checkout, /Máy vặn vít pin Bosch GO 3/);
assert.match(checkout, /Máy hút bụi cầm tay Deerma DX118C 600W/);
assert.match(checkout, /lm-product-deals/);

const finance = read('site-v2/finance-gate.js');
assert.match(finance, /deep_engagement_secondary_offer/);
assert.match(finance, /affiliate_finance_view/);
assert.match(finance, /affiliate_finance_click/);
assert.match(finance, /MIN_DELAY_MS = 60000/);
assert.match(finance, /MIN_SCROLL_RATIO = 0\.72/);
assert.match(finance, /COOLDOWN_MS = 7 \* 24 \* 60 \* 60 \* 1000/);
assert.match(finance, /isPaidAcquisitionVisit/);
assert.match(finance, /hasAiIntent/);
assert.match(finance, /AI_INTENT_KEY/);
assert.match(finance, /AFFILIATE_INTENT_KEY/);
assert.match(finance, /LAST_SHOWN_KEY/);
assert.match(finance, /data-open-checkout/);
assert.match(finance, /data-ai-sticky-cta/);
assert.match(finance, /role", "complementary/);
assert.doesNotMatch(finance, /body\.lm-finance-gate-open|position:fixed;inset:0|EARLY_DELAY_MS = 12000|EARLY_SCROLL_PX = 120/);

const homeBuilder = read('scripts/apply_home_portal_safe.py');
assert.match(homeBuilder, /data-ai-commerce-trust/);
assert.match(homeBuilder, /data-ai-product-proof/);
assert.match(homeBuilder, /data-ai-sticky-cta/);
assert.match(homeBuilder, /mô tả lịch sử, không phải xác suất hay cam kết/i);

console.log('ADAPTIVE_AI_AFFILIATE_COMMERCE_POLICY_OK');
