# Consumer migration and parity

The standalone producer supersedes pricing ownership in EV Charge Manager #4 and
#7–#10. Its upstream PR #11/#12 implementation is reused here, not rebuilt in the
consumer. Manager's vehicle/session/planning/charging policy stays in that repository.
The 30-minute optimizer cycle and earliest-start tie-break remain consumer behavior.

API v1 supplies final VAT-inclusive DKK/kWh slots by configured producer site ID.
An EV adapter must discover the loaded producer, request one range, accept READY
complete coverage only, map final values to its PriceSlot type and subscribe to
future price-revision events. No supplier/DSO selection, HTTP retrieval, VAT or tariff
arithmetic belongs in that adapter. Unloaded, stale, errored and incomplete results
cause explicit unavailable/deferred planning and bounded discovery retry. Do not
fall back silently to a second price owner.

Tests in this repository exercise independent multi-site mapping, frozen range
results, unloaded discovery, negative prices, DST, earliest-slot ranking, VAT,
Radius seasonal/timeband fixtures and source failures. Shared original fixtures and
regressions provide producer parity with EV Manager PR #12's tested calculations.
This proves fixture parity, not a comparison to the owner's actual live broker.

A separately reviewed EV Manager consumer PR and its tests remain part of #5.
Read-only exported Node-RED Energy Price Broker/real_energy_price sample inputs and
outputs are needed for household/summer-house end-to-end parity. Do not fetch them
from running HA or Node-RED without authorization. Never manufacture contract
values or claim live parity from synthetic inputs. No production switch is implied
by an adapter or passing tests. Legacy Node-RED remains untouched.
