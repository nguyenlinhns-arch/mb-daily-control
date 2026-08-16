import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const read = path => readFileSync(path, 'utf8');

assert.equal(
  existsSync('site-v2/finance-gate.js'),
  false,
  'Intrusive finance gate source must not exist in the production repository'
);

const conversion = read('scripts/apply_conversion_v2.py');
assert.doesNotMatch(conversion, /FINANCE_GATE_SCRIPT_TAG|finance_gate_source|copy2\([^\n]*finance_gate/i);
assert.doesNotMatch(conversion, /inject_before_head_end\([^\n]*FINANCE_GATE/i);
assert.match(conversion, /finance-banner\.js/);
assert.match(conversion, /Intrusive finance gate leaked into production homepage/);

const commerce = read('site-v2/finance-banner.js');
assert.match(commerce, /affiliate-shopee-smartlink/);
assert.match(commerce, /affiliate_shopee_view/);
assert.match(commerce, /affiliate_shopee_click/);
assert.match(commerce, /ai_checkout_intent/);
assert.match(commerce, /MỞ BẢN PHÂN TÍCH AI/);
assert.match(commerce, /30\.000đ/);
assert.doesNotMatch(
  commerce,
  /lm-finance-gate|VAY TIỀN NHANH|vay online|lãi suất từ 1,2%|position:fixed;inset:0/i
);

const homeBuilder = read('scripts/apply_home_portal_safe.py');
assert.match(homeBuilder, /data-ai-commerce-trust/);
assert.match(homeBuilder, /data-ai-product-proof/);
assert.match(homeBuilder, /data-ai-sticky-cta/);
assert.match(homeBuilder, /mô tả lịch sử, không phải xác suất hay cam kết/i);

console.log('AI_FIRST_COMMERCE_POLICY_OK');
