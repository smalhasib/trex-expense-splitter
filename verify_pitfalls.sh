#!/bin/bash
# Comprehensive verification of all 7 pitfalls
# Resets DB between sections for predictable IDs

cleanup() { rm -f ~/.tourexpenses/expenses.db; }
trap cleanup EXIT

PASS=0
FAIL=0

assert_contains() {
  if echo "$1" | grep -qE "$2"; then
    echo "  ✅ PASS: $3"
    PASS=$((PASS+1))
  else
    echo "  ❌ FAIL: $3 (expected to match regex '$2')"
    echo "    Got: $(echo "$1" | head -3)"
    FAIL=$((FAIL+1))
  fi
}

assert_not_contains() {
  if echo "$1" | grep -q "$2"; then
    echo "  ❌ FAIL: $3"
    FAIL=$((FAIL+1))
  else
    echo "  ✅ PASS: $3"
    PASS=$((PASS+1))
  fi
}

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 1: Mid-trip joiner auto-defaults to today"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "Trip" --people "Alice,Bob" > /dev/null
trex exp add 100 --desc "Dinner" --paid Alice -t 1 -D "2026-06-20" --cat "Food & Drink" > /dev/null
trex trip people add "Charlie" -t 1 > /dev/null
trex exp add 120 --desc "Lunch" --paid Bob -t 1 -D "$(date +%Y-%m-%d)" --cat "Food & Drink" > /dev/null
SHARES=$(trex exp shares 2 2>&1)
assert_contains "$SHARES" "Alice.*৳40.00" "Alice in today's expense (৳40.00 share)"
assert_contains "$SHARES" "Charlie.*৳40.00" "Charlie in today's expense (৳40.00 share)"
assert_contains "$SHARES" "Bob.*৳40.00" "Bob in today's expense (৳40.00 share)"

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 2: Soft-delete participants with history"
echo "─────────────────────────────────────────────────────────"
trex trip people remove "Alice" -t 1 > /dev/null
LIST=$(trex trip people list -t 1 2>&1)
assert_not_contains "$LIST" "Alice" "Alice removed from active list"
SUMMARY=$(trex summary 1 2>&1)
assert_contains "$SUMMARY" "Alice" "Alice still in settlement math"
assert_contains "$SUMMARY" "৳100.00" "Alice's payment preserved"

# Hard-delete test (no expenses)
trex trip people add "David" -t 1 > /dev/null
trex trip people remove "David" -t 1 > /dev/null
DB=$(python3 -c "
import sqlite3
c = sqlite3.connect('/home/ubuntu/.tourexpenses/expenses.db')
c.row_factory = sqlite3.Row
print(','.join(r['name'] for r in c.execute('SELECT name FROM participants WHERE trip_id = 1')))
")
[ "$DB" = "Alice,Bob,Charlie" ] && echo "  ✅ PASS: David hard-deleted (no row)" && PASS=$((PASS+1)) \
  || { echo "  ❌ FAIL: David not deleted"; FAIL=$((FAIL+1)); }

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 3: --for typo rejected"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "Trip" --people "Alice,Nabila" > /dev/null
OUT=$(trex exp add 100 --desc "Breakfast" --paid Alice -t 1 --cat "Food & Drink" --for "Alice,Nabil" 2>&1 || true)
assert_contains "$OUT" "Error: --for contains unknown names" "Typo rejected with clear error"

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 4: exp update command"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "Trip" --people "Alice,Bob,Charlie" > /dev/null
trex exp add 300 --desc "Original" --paid Alice -t 1 --cat "Food & Drink" > /dev/null
trex exp update 1 --desc "Updated" > /dev/null
trex exp update 1 --amount 600 > /dev/null 2>&1
SHARES=$(trex exp shares 1 2>&1)
assert_contains "$SHARES" "৳200.00" "Shares recalculated to ৳200 each"

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 5: trip reopen command"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "Trip" --people "A,B" > /dev/null
trex exp add 100 --desc "X" --paid A -t 1 --cat "Food & Drink" > /dev/null
trex trip end 1 > /dev/null
trex trip reopen 1 > /dev/null
REOPENED=$(trex trip list 2>&1)
assert_contains "$REOPENED" "Trip" "Reopened trip appears in active list"

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 6: Single currency per trip (documented)"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "USD Trip" --currency USD --people "X,Y" > /dev/null
EXP=$(trex exp add 100 --desc "Test" --paid X -t 1 --cat "Food & Drink" 2>&1)
assert_contains "$EXP" '\$100.00' "USD trip uses dollar sign"
HELP=$(trex exp add --help 2>&1)
assert_not_contains "$HELP" "currency" "No --currency flag on exp add"

# ═══════════════════════════════════════════════════════════
echo ""
echo "▶ PITFALL 7: Custom split sum validation"
echo "─────────────────────────────────────────────────────────"
cleanup
trex trip start "Trip" --people "Alice,Bob,Charlie" > /dev/null
# Correct sum: 100+100+100=300 → should accept
printf "100\n100\n100\n" | trex exp add 300 --desc "Valid" --paid Alice -t 1 --cat "Shopping" --split custom > /dev/null 2>&1
SHARES=$(trex exp shares 1 2>&1)
assert_contains "$SHARES" "৳100.00" "Valid custom sum accepted"

# ═══════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  RESULTS: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════════════"
exit $FAIL
