import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const read = path => readFileSync(path, 'utf8');

assert.equal(
  existsSync('site-v2/finance-gate.js'),
  true,
  'Mobile finance affiliate gate source must exist'
);

const conversion = read('scripts/apply_conversion_v2.py');
assert.match(conversion, /finance-gate\.js/);
assert.match(conversion, /FINANCE_GATE_SCRIPT_TAG/);
assert.match(conversion, /finance-banner\.js/);
assert.doesNotMatch(conversion, /Intrusive finance gate leaked into production homepage/);

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

const financeGate = read('site-v2/finance-gate.js');
assert.match(financeGate, /after_latest_results_gate/);
assert.match(financeGate, /affiliate_finance_gate_view/);
assert.match(financeGate, /affiliate_finance_click/);
assert.match(financeGate, /Vay tiền mặt online nhanh/);
assert.match(financeGate, /VAY TIỀN NHANH ONLINE/);
assert.match(financeGate, /Đóng để xem tiếp/);
assert.match(financeGate, /align-items:flex-end/);
assert.match(financeGate, /max-height:88svh/);
assert.match(financeGate, /EARLY_DELAY_MS = 12000/);
assert.match(financeGate, /EARLY_SCROLL_PX = 120/);

const homeBuilder = read('scripts/apply_home_portal_safe.py');
assert.match(homeBuilder, /data-ai-commerce-trust/);
assert.match(homeBuilder, /data-ai-product-proof/);
assert.match(homeBuilder, /data-ai-sticky-cta/);
assert.match(homeBuilder, /mô tả lịch sử, không phải xác suất hay cam kết/i);

console.log('AI_PLUS_AFFILIATE_COMMERCE_POLICY_OK');
