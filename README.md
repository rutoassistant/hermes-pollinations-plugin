# Pollinations Image Generation Plugin for Hermes Agent

Free image generation provider plugin for Hermes Agent using [Pollinations.ai](https://pollinations.ai).

Supports both authenticated API (higher rate limits) and legacy free endpoint (no key required).

## Features

- No API key required for basic usage
- Multiple models: `flux` (high quality), `klein` (fast), `zimage` (artistic)
- Automatic fallback from authenticated API to free legacy endpoint
- Compatible with Hermes Agent's `image_generate` tool
- Supports aspect ratios: `square`, `landscape`, `portrait`

## Installation

1. Copy the plugin directory to your Hermes plugins folder:
```bash
cp -r /path/to/plugins/image_gen/pollinations /opt/data/plugins/image_gen/pollinations/
```

2. Enable the plugin in your Hermes config:
```bash
hermes config set plugins.enabled '["image_gen/pollinations"]'
hermes config set image_gen.provider pollinations
```

3. Restart the Hermes gateway:
```bash
hermes gateway restart
```

4. Verify the plugin loaded:
```bash
hermes config get image_gen.provider
```

## Configuration

### Optional: API Key

For higher rate limits, add your Pollinations API key to Hermes `.env`:

```bash
echo "POLLINATIONS_API_KEY=sk_..." >> /opt/data/.env
```

Get an API key at: https://enter.pollinations.ai

Without an API key, the plugin uses the public free endpoint (1 request per 15 seconds).

## Usage

Use the `image_generate` tool in Hermes:

```
Generate an image of a sunset over mountains, aspect ratio landscape, model flux
```

### Models

| Model ID | Display Name | Speed | Best For |
|----------|-------------|-------|----------|
| `flux` | Flux | ~5-10s | High quality, photorealistic |
| `klein` | Klein | ~2-5s | Fast generations |
| `zimage` | Z-Image | ~3-8s | Artistic styles |

## Rate Limits

| Tier | Limit |
|------|-------|
| Anonymous (no key) | 1 request per 15 seconds |
| Authenticated | Higher limits (see Pollinations dashboard) |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Provider not found` | Plugin not loaded | Restart gateway, check `plugins.enabled` |
| Empty response | Rate limited | Wait 15s and retry |
| HTML instead of image | Rate limit error page | Check file size, add delay |

## Files

- `__init__.py` — Provider implementation
- `plugin.yaml` — Plugin metadata

## License

MIT

## Related

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Pollinations.ai: https://pollinations.ai
