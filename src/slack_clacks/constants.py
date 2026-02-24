from decimal import Decimal

# Smallest timestamp increment in Slack.
# Slack message timestamps have microsecond precision (6 decimal places).
# Used to convert inclusive timestamp boundaries to exclusive ones.
#
# We use Decimal rather than float because Slack timestamps like
# "1768309560.198419" exceed float64 precision (~15-16 significant digits).
# float("1768309560.198419") + 0.000001 produces "1768309560.19842" (rounds
# the last digit away), which fails to exclude the boundary message.
# Decimal preserves all digits exactly.
SLACK_TS_EPSILON = Decimal("0.000001")
