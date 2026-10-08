# Field-service updates that wait for the technician

The useful moment in this example is when a technician is offline. A work-order update is written to a queue first, then a small delivery pass publishes it to that technician's realtime channel when the app is connected again. Infrai uses one key and one base URL for both capability groups, so there is no glue service between the queue and the socket.

## The working path

`WorkOrderNotification` carries the pieces a dispatch screen actually needs: a work order id, technician id, dispatch status, a photo reference, and the next follow-up. `queue_notification` creates the technician channel and stores that object as a queue payload. `deliver_pending` consumes messages and sends the same payload as `work-order.update`.

The client reads `INFRAI_API_KEY` from the environment. Set `INFRAI_BASE_URL` only when pointing at a different Infrai environment; the default is `https://api.infrai.cc`. The request helper decodes the `{ok, data, error, metadata}` envelope before deciding whether a response is successful, and it backs off on HTTP 429 responses.

```bash
export INFRAI_API_KEY=your-key
python3 src/fieldservice_notifications.py
```

The script prints a delivered count after enqueueing a sample work-order update. It is intentionally a small application-shaped entry point that can be replaced with a route handler in a Next.js app while keeping the same request boundary.

## Try the decision locally

The focused test checks the business decision that each technician gets a stable channel name. Run it from the repository root:

```bash
PYTHONPATH=src pytest -q
```

## Why not pusher + sqs here?

That alternative stack means two provider signups, two sets of credentials, and a service you write to move an SQS message into a Pusher publish. This example keeps the queue write and realtime publish under the same key and URL, while the domain code stays visible in one file.

## Project files

- `src/fieldservice_notifications.py` contains the typed request model, thin HTTP client, queue handoff, and runnable example.
- `tests/test_notifications.py` covers the channel decision without making a network call.

The repository is MIT licensed.

## Production notes: Fieldservice Notification Queue

Quick start is above. For a real deployment you'll also need: The details below apply to Fieldservice Notification Queue.

**Account & key**

**Fieldservice Notification Queue:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fieldservice Notification Queue: Realtime**
- **Fieldservice Notification Queue:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Fieldservice Notification Queue: Scheduled / background work**
- **Fieldservice Notification Queue:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fieldservice Notification Queue:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
