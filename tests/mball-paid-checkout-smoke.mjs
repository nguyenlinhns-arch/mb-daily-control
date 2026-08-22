import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(path, 'utf8');

const builder = read('scripts/optimize_portal_v2_run.py');
assert.match(builder, /THANH TOÁN NHẬN GỢI Ý SỐ/);
assert.match(builder, /30\.000đ\/ngày/);
assert.match(builder, /Xác nhận thanh toán qua email/);
assert.match(builder, /data-open-checkout/);
assert.match(builder, /zalo_support_only/);
assert.doesNotMatch(builder, /data-zalo-suggestion-section/);
assert.doesNotMatch(builder, /window\.open\(u/);

const copyLock = read('site-v2/copy-lock.js');
assert.match(copyLock, /THANH TOÁN NHẬN GỢI Ý SỐ/);
assert.match(copyLock, /xác nhận thanh toán qua email/i);
assert.match(copyLock, /Zalo chỉ dùng để hỗ trợ/);
assert.doesNotMatch(copyLock, /routeButtonToZalo/);
assert.doesNotMatch(copyLock, /installZaloRouting/);
assert.doesNotMatch(copyLock, /MỞ ZALO – NHẬN GỢI Ý HÔM NAY/);
assert.doesNotMatch(copyLock, /window\.open\(/);

const checkoutEntry = read('site-v2/checkout-entry.js');
assert.match(checkoutEntry, /button\.click\(\)/);
assert.match(checkoutEntry, /checkout\.hidden = false/);
assert.doesNotMatch(checkoutEntry, /ZALO_ROUTE/);
assert.doesNotMatch(checkoutEntry, /location\.replace\(.*zalo/i);

console.log('MBALL_PAID_CHECKOUT_EMAIL_CONFIRMATION_OK');
