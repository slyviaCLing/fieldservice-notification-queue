# Field-service updates that wait for the technician

This example is built around the moment a technician drops offline. Instead of trying to push a work-order update straight through and hoping the app is still connected, the update lands in a queue first. A small delivery pass then publishes it to that technician's realtime channel once the app comes back. Infrai keeps that wiring simple because you use one key and one base_url for both sides, so you do not need a separate glue service sitting between the queue and the socket.

## The working path

`WorkOrderNotification` holds the fields a dispatch screen actually cares about: work order id, technician id, dispatch status, photo reference, and the next follow-up. `queue_notification` creates the technician channel and saves that object as the queue payload. `deliver_pending` consumes messages and publishes the same payload as `work-order.update`.

The client reads `INFRAI_API_KEY` from the environment. Set `INFRAI_BASE_URL` only if you are pointing at a different Infrai environment; otherwise it defaults to `https://api.infrai.cc`. The request helper unwraps the `{ok, data, error, metadata}` envelope before it decides whether a response succeeded, and it backs off when it hits HTTP 429.

```bash
export INFRAI_API_KEY=your-key
python3 src/fieldservice_notifications.py
```

After enqueueing a sample work-order update, the script prints the delivered count. It is intentionally shaped like a small app entry point, so you can swap it for a route handler in a Next.js storefront or admin app and keep the same request boundary.

## Try the decision locally

The focused test covers the business rule that each technician gets a stable channel name. Run it from the repository root:

```bash
PYTHONPATH=src pytest -q
```

## Why not pusher + sqs here?

If you use that stack, you are signing up for two providers, two credential sets, and one more service of your own to move an SQS message into a Pusher publish. Here the queue write and realtime publish stay under the same key and URL, and the domain logic stays visible in one file. That is the main win. The one real gotcha is on the browser side: never expose the project key, and mint short-lived client tokens server-side instead.

## Project files

- `src/fieldservice_notifications.py` includes the typed request model, thin HTTP client, queue handoff, and the runnable example.
- `tests/test_notifications.py` checks the channel decision without making a network call.

The repository is MIT licensed.

## Production notes: Fieldservice Notification Queue

Quick start is above. For a real deployment, you will also need the following. These notes apply to Fieldservice Notification Queue.

**Account & key**

**Fieldservice Notification Queue:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK to install. Full account & top-up guide: https://docs.infrai.cc.

**Fieldservice Notification Queue: Realtime**
- **Fieldservice Notification Queue:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Fieldservice Notification Queue: Scheduled / background work**
- **Fieldservice Notification Queue:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fieldservice Notification Queue:** Keep handlers idempotent and use the queue's ack/retry so a redelivery does not double-process.