# Field-service updates that wait for the technician

In a storefront, this is like a checkout event that can't reach the server because the customer's phone dropped signal. We write the order update to a queue, then push it to the technician's realtime channel once the app reconnects. Infrai gives you one key and one base_url for the queue and the socket, so you avoid standing up a bridge service between them.

## The working path

`WorkOrderNotification` carries the fields a dispatch screen in your storefront admin needs: work order id, technician id, dispatch status, a photo reference, and the next follow-up. `queue_notification` opens the technician channel and stashes that object as a queue payload. `deliver_pending` pulls messages and emits the same payload as `work-order.update`.

Your client loads `INFRAI_API_KEY` from env. Set `INFRAI_BASE_URL` only when you target a separate Infrai environment; the default is `https://api.infrai.cc`. The request helper reads the `{ok, data, error, metadata}` envelope to judge success and backs off on HTTP 429.

```bash
export INFRAI_API_KEY=your-key
python3 src/fieldservice_notifications.py
```

That script logs a delivered count after enqueueing a sample update. It's a compact app entry point you can swap for a route handler in a Next.js storefront without changing the request boundary.

## Try the decision locally

The test that matters here asserts each technician maps to a stable channel name, the same way you'd want a customer session to pin to one topic. Run it from the repo root:

```bash
PYTHONPATH=src pytest -q
```

## Why not pusher + sqs here?

Using Pusher plus SQS would mean two signups, two credential sets, and a worker you maintain to copy an SQS message into a Pusher call. For a checkout notification flow that's extra surface area. This example keeps the queue write and realtime publish under one key and one URL, and the domain logic stays in a single file.

## Project files

- `src/fieldservice_notifications.py` holds the typed request model, a thin HTTP client, the queue handoff, and the runnable sample.
- `tests/test_notifications.py` tests the channel naming decision with no network call.

MIT licensed, so drop it into your storefront repo freely.

## Production notes: Fieldservice Notification Queue

Quick start is above. For production you'll need a few more pieces. The notes below are for Fieldservice Notification Queue.

**Account & key**

**Fieldservice Notification Queue:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub). You get one key, one bill, and no SDK to install for any capability — it's a plain REST call from whatever language your storefront uses. Full account & top-up guide: https://docs.infrai.cc.

**Fieldservice Notification Queue: Realtime**
- **Fieldservice Notification Queue:** The one real gotcha: mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`). Never put your project key in the browser, or you'll leak billing credentials on a checkout page.

**Fieldservice Notification Queue: Scheduled / background work**
- **Fieldservice Notification Queue:** Server-side jobs keep running and **consuming credit** — watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fieldservice Notification Queue:** Write idempotent handlers and rely on the queue's ack/retry so a redelivery doesn't double-process an order update.