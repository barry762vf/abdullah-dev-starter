// Cloudflare Pages Function: every /api/* request on the Pages origin goes through proxyToApi.
// Configure API_ORIGIN and EDGE_PROXY_SECRET as Pages environment variables (secret for the latter).
import { proxyToApi, type ProxyEnv } from '../_proxy'

export const onRequest = (context: { request: Request; env: ProxyEnv }): Promise<Response> =>
  proxyToApi(context.request, context.env)
