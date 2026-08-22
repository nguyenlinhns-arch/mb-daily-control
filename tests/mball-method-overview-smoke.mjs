import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const runtime = readFileSync('site-v2/copy-lock.js', 'utf8');

assert.match(runtime, /function\s+normalizeMballMethodOverview/);
assert.match(runtime, /MB_ALL chạy đủ 31 phương pháp mỗi ngày/);
assert.match(runtime, /data-mball31-process/);
assert.match(runtime, /3–5–7–10/);
assert.match(runtime, /HOT\/COLD/);
assert.match(runtime, /PRE-DRAW/);
assert.match(runtime, /portal-method-numbers,\.portal-ball,\.portal-consensus/);
assert.match(runtime, /Đầu ra 31 phương pháp và số cuối được giữ kín/);
assert.match(runtime, /Chỉ mở sau khi thanh toán được xác nhận qua email/);
assert.doesNotMatch(runtime, /setText\(heading,\s*`Gợi ý số hôm nay/);

console.log('MBALL_31_METHOD_OVERVIEW_RUNTIME_OK');
