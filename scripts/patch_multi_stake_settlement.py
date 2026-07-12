#!/usr/bin/env python3
"""Patch settlement engine for per-code points and multi-method real orders."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/sync_from_google_sheet.py"
MARKER = "PER_CODE_MULTI_METHOD_SETTLEMENT_V2"

CALCULATE = r'''def calculate_settlement(doc: dict[str, Any], order: dict[str, Any], draw_date: date, codes: list[str]) -> dict[str, Any]:
    """PER_CODE_MULTI_METHOD_SETTLEMENT_V2: settle each code at its confirmed stake."""
    freq = Counter(codes)
    stake = doc.get('stake_rule') or {}
    lo = order.get('lo') or {}
    numbers = dedupe([str(code2(x)).zfill(2) for x in lo.get('numbers', []) if code2(x)])
    fallback_points = as_int(lo.get('points_per_code'), as_int(stake.get('lo_points_per_code'), 50))
    raw_map = lo.get('points_by_code') or {}
    points_by_code = {
        number: as_int(raw_map.get(number), fallback_points)
        for number in numbers
    }
    if any(points <= 0 for points in points_by_code.values()):
        raise RuntimeError(f'Điểm theo mã không hợp lệ: {points_by_code}')
    lo_cost_pp = as_int(stake.get('lo_cost_per_point_vnd'), 23000)
    lo_pay_pp = as_int(stake.get('lo_payout_per_hit_point_vnd'), 80000)
    hits = {number: freq.get(number, 0) for number in numbers}
    lo_capital = sum(points_by_code[number] * lo_cost_pp for number in numbers)
    lo_payout = sum(hits[number] * points_by_code[number] * lo_pay_pp for number in numbers)
    lo_pnl = lo_payout - lo_capital
    uniform = len(set(points_by_code.values())) <= 1
    display_points = next(iter(points_by_code.values()), 0) if uniform else 0

    xien = order.get('xien2') or {}
    raw_pairs = xien.get('pairs') or []
    if not raw_pairs:
        base_numbers = [str(code2(x)).zfill(2) for x in xien.get('base_numbers', []) if code2(x)]
        if not base_numbers:
            base_numbers = numbers
        raw_pairs = [f'{a}-{b}' for a, b in combinations(dedupe(base_numbers), 2)] if xien.get('auto_combinations') else []
    pairs = dedupe([normalise_pair(pair) for pair in raw_pairs])
    xien_points = as_int(xien.get('points_per_pair'), as_int(stake.get('xien2_points_per_pair'), 100))
    pair_capital = as_int(stake.get('xien2_capital_per_pair_vnd'), 100000)
    pair_return = as_int(stake.get('xien2_gross_return_per_winning_pair_vnd'), 1600000)
    winning_pairs = [pair for pair in pairs if all(freq.get(leg, 0) > 0 for leg in pair.split('-', maxsplit=1))]
    xien_capital = len(pairs) * pair_capital
    xien_payout = len(winning_pairs) * pair_return
    xien_pnl = xien_payout - xien_capital
    return {
        'date': draw_date.isoformat(),
        'result_sha256': json_hash(codes),
        'result_codes': codes,
        'lo': {
            'numbers': numbers,
            'points_per_code': display_points,
            'points_mode': 'UNIFORM' if uniform else 'PER_CODE',
            'points_by_code': points_by_code,
            'hits': hits,
            'hits_total': sum(hits.values()),
            'capital_vnd': lo_capital,
            'payout_vnd': lo_payout,
            'pnl_vnd': lo_pnl,
        },
        'xien2': {
            'pairs': pairs,
            'points_per_pair': xien_points,
            'winning_pairs': winning_pairs,
            'wins': len(winning_pairs),
            'losses': len(pairs) - len(winning_pairs),
            'capital_per_pair_vnd': pair_capital,
            'gross_return_per_winning_pair_vnd': pair_return,
            'capital_vnd': xien_capital,
            'payout_vnd': xien_payout,
            'pnl_vnd': xien_pnl,
        },
        'total_capital_vnd': lo_capital + xien_capital,
        'total_payout_vnd': lo_payout + xien_payout,
        'total_pnl_vnd': lo_pnl + xien_pnl,
        'components': copy.deepcopy(order.get('components') or []),
    }
'''

UPDATE_SUMMARY = r'''def update_pnl_summary(doc: dict[str, Any], record: dict[str, Any], delta_lo: int, delta_xien: int) -> None:
    q = doc.setdefault('pnl_summary', {})
    total_delta = delta_lo + delta_xien
    for key in ('five_group_pnl_vnd', 'active_five_group_pnl_vnd'):
        if key in q:
            q[key] = as_int(q[key]) + delta_xien
    q['user_lo_pnl_vnd'] = as_int(q.get('user_lo_pnl_vnd'), 0) + delta_lo
    if 'active_all_real_pnl_vnd' in q:
        q['active_all_real_pnl_vnd'] = as_int(q['active_all_real_pnl_vnd']) + total_delta
    elif 'active_five_group_pnl_vnd' in q:
        q['active_all_real_pnl_vnd'] = as_int(q['active_five_group_pnl_vnd']) + as_int(q.get('user_lo_pnl_vnd'), 0)
    if 'grand_total_pnl_vnd' in q:
        q['grand_total_pnl_vnd'] = as_int(q['grand_total_pnl_vnd']) + total_delta
    elif 'active_all_real_pnl_vnd' in q:
        q['grand_total_pnl_vnd'] = as_int(q['active_all_real_pnl_vnd']) + as_int(q.get('archive_pnl_vnd'), 0)
    lo = record['lo']
    xien = record['xien2']
    stake_text = ', '.join(f"{code}×{lo['points_by_code'][code]}" for code in lo['numbers']) or 'Không có lô'
    if xien['pairs']:
        stake_text += f" + {len(xien['pairs'])} cặp Xiên ×{xien['points_per_pair']}"
    q.update({
        'confirmed_through': record['date'],
        'yesterday_date': record['date'],
        'yesterday_pnl_vnd': record['total_pnl_vnd'],
        'yesterday_hits': lo['hits_total'],
        'yesterday_stake': stake_text,
        'today_pending_capital_vnd': 0,
        'today_pending_order': f"Đã chốt P/L ngày: {signed_vnd(record['total_pnl_vnd'])}",
        'today_included': True,
    })
'''

FULL_DISPLAY = r'''def full_settlement_display(doc: dict[str, Any], order: dict[str, Any], record: dict[str, Any]) -> None:
    lo = record['lo']
    xien = record['xien2']
    numbers = lo['numbers']
    pairs = xien['pairs']
    total_pnl = record['total_pnl_vnd']
    settled_at = now_vn().isoformat(timespec='seconds')
    order_lo = order.setdefault('lo', {})
    order_lo.update({
        'numbers': numbers,
        'points_per_code': lo['points_per_code'],
        'points_mode': lo['points_mode'],
        'points_by_code': lo['points_by_code'],
        'hits': lo['hits'],
        'code_count': len(numbers),
        'capital_vnd': lo['capital_vnd'],
        'payout_vnd': lo['payout_vnd'],
        'pnl_vnd': lo['pnl_vnd'],
    })
    order_xien = order.setdefault('xien2', {})
    order_xien.update({
        'pairs': pairs,
        'points_per_pair': xien['points_per_pair'],
        'winning_pairs': xien['winning_pairs'],
        'wins': xien['wins'],
        'losses': xien['losses'],
        'capital_vnd': xien['capital_vnd'],
        'payout_vnd': xien['payout_vnd'],
        'pnl_vnd': xien['pnl_vnd'],
    })
    order.update({
        'status': 'REAL_SETTLED_WIN' if total_pnl > 0 else 'REAL_SETTLED_LOSS' if total_pnl < 0 else 'REAL_SETTLED_EVEN',
        'settled_at': settled_at,
        'pnl_included': True,
        'total_capital_vnd': record['total_capital_vnd'],
        'total_payout_vnd': record['total_payout_vnd'],
        'total_pnl_vnd': total_pnl,
        'note': f"Lô {lo['hits_total']} nháy; Xiên thắng {xien['wins']}/{len(pairs)} cặp.",
    })
    doc['settlement'] = {
        'date': record['date'],
        'result_codes': record['result_codes'],
        'result_sha256': record['result_sha256'],
        'lo_hits_total': lo['hits_total'],
        'lo_points_by_code': lo['points_by_code'],
        'xien_wins': xien['wins'],
        'lo_pnl_vnd': lo['pnl_vnd'],
        'xien_pnl_vnd': xien['pnl_vnd'],
        'total_pnl_vnd': total_pnl,
    }
    doc.pop('pending_order', None)
    total_points = sum(lo['points_by_code'].values()) + xien['points_per_pair'] * len(pairs)
    doc['portfolio'] = {
        'decision': 'SETTLED_ACTUAL_ORDER',
        'tier': 'KẾT QUẢ ĐÃ KHÓA',
        'selection': '-'.join(numbers) if numbers else '|'.join(pairs),
        'title': f"KẾT QUẢ {datetime.strptime(record['date'], '%Y-%m-%d').strftime('%d/%m')}: {signed_vnd(total_pnl)}",
        'points': total_points,
        'capital_vnd': record['total_capital_vnd'],
        'payout_vnd': record['total_payout_vnd'],
        'pnl_vnd': total_pnl,
        'reason': order['note'],
        'pnl_status': 'SETTLED',
    }

    methods: list[dict[str, Any]] = []
    components = order.get('components') or []
    if components:
        pay_pp = as_int((doc.get('stake_rule') or {}).get('lo_payout_per_hit_point_vnd'), 80000)
        cost_pp = as_int((doc.get('stake_rule') or {}).get('lo_cost_per_point_vnd'), 23000)
        for component in components:
            component_numbers = [str(code2(x)).zfill(2) for x in component.get('selection', []) if code2(x)]
            component_map = {code: as_int((component.get('points_by_code') or {}).get(code), as_int(lo['points_by_code'].get(code))) for code in component_numbers}
            component_capital = sum(component_map[code] * cost_pp for code in component_numbers)
            component_payout = sum(lo['hits'].get(code, 0) * component_map[code] * pay_pp for code in component_numbers)
            component_pnl = component_payout - component_capital
            methods.append({
                'id': f"RESULT_{component.get('method_id', 'USER')}",
                'label': component.get('label') or component.get('method_id') or 'Lô thực chiến',
                'method': ' · '.join(f"{code}×{component_map[code]}" for code in component_numbers),
                'status': 'SETTLED_WIN' if component_pnl > 0 else 'SETTLED_LOSS' if component_pnl < 0 else 'SETTLED_EVEN',
                'points_per_code': next(iter(component_map.values()), 0) if len(set(component_map.values())) <= 1 else 'Theo mã',
                'code_count': len(component_numbers),
                'capital_vnd': component_capital,
                'payout_vnd': component_payout,
                'pnl_vnd': component_pnl,
                'numbers': [
                    {
                        'code': code,
                        'points': component_map[code],
                        'capital_vnd': component_map[code] * cost_pp,
                        'role': f"{lo['hits'].get(code, 0)} nháy",
                    }
                    for code in component_numbers
                ],
            })
    elif numbers:
        methods.append({
            'id': 'USER_LO',
            'label': 'Lô thực chiến',
            'method': ' · '.join(f"{code}×{lo['points_by_code'][code]}" for code in numbers),
            'status': order['status'],
            'points_per_code': lo['points_per_code'] or 'Theo mã',
            'code_count': len(numbers),
            'capital_vnd': lo['capital_vnd'],
            'numbers': [
                {
                    'code': number,
                    'points': lo['points_by_code'][number],
                    'capital_vnd': lo['points_by_code'][number] * as_int((doc.get('stake_rule') or {}).get('lo_cost_per_point_vnd'), 23000),
                    'role': f"{lo['hits'][number]} nháy",
                }
                for number in numbers
            ],
        })
    if pairs:
        methods.append({
            'id': 'USER_XIEN2',
            'label': 'Xiên 2 thực chiến',
            'method': f"{len(pairs)} cặp ×{xien['points_per_pair']} điểm",
            'status': 'SETTLED_WIN' if xien['wins'] else 'SETTLED_LOSS',
            'points_per_code': xien['points_per_pair'],
            'code_count': len(pairs),
            'capital_vnd': xien['capital_vnd'],
            'numbers': [
                {
                    'code': pair,
                    'points': xien['points_per_pair'],
                    'capital_vnd': as_int((doc.get('stake_rule') or {}).get('xien2_capital_per_pair_vnd'), 100000),
                    'role': 'Trúng' if pair in xien['winning_pairs'] else 'Trượt',
                }
                for pair in pairs
            ],
        })
    doc['top_signals'] = {
        'title': 'KẾT QUẢ THỰC CHIẾN ĐÃ CHỐT',
        'subtitle': f"Lô {signed_vnd(lo['pnl_vnd'])} · Xiên 2 {signed_vnd(xien['pnl_vnd'])} · Tổng {signed_vnd(total_pnl)}",
        'total_methods': len(methods),
        'total_numbers': f"{len(numbers)} số + {len(pairs)} cặp",
        'total_points': f"{sum(lo['points_by_code'].values())} lô + {xien['points_per_pair'] * len(pairs)} xiên",
        'total_capital_vnd': record['total_capital_vnd'],
        'note': order['note'],
        'methods': methods,
    }
    doc['top_signal_policy'] = {
        'mode': 'SETTLED_ACTUAL_ORDER',
        'system_signals_preserved_in_groups': True,
        'pnl_rule': 'Đã cộng kết quả đúng một lần vào sổ xác nhận.',
        'settlement_rule_version': 'PER_CODE_MULTI_METHOD_SETTLEMENT_V2',
    }
'''


def replace_block(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_block(text, "def calculate_settlement(", "def default_ledger(", CALCULATE)
    text = replace_block(text, "def update_pnl_summary(", "def update_ledger_snapshot(", UPDATE_SUMMARY)
    text = replace_block(text, "def full_settlement_display(", "def settle_order(", FULL_DISPLAY)
    TARGET.write_text(text, encoding="utf-8")
    assert MARKER in text
    print("MULTI_STAKE_SETTLEMENT_PATCH_APPLIED")


if __name__ == "__main__":
    main()
