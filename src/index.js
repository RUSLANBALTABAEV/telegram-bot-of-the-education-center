// ============ src/index.js ============
/**
 * Cloudflare Worker для проксирования webhook от Telegram
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const token = env.BOT_TOKEN;
    const pythonBackend = env.PYTHON_BACKEND;

    // Логируем входящий запрос
    console.log(`📨 Входящий запрос: ${request.method} ${url.pathname}`);

    // ============ WEBHOOK ENDPOINT ============
    if (request.method === 'POST' && url.pathname === '/webhook') {
      try {
        // Получаем данные от Telegram
        const update = await request.json();
        const updateId = update.update_id;

        console.log(`🔄 Обработка update #${updateId}...`);

        // Проверяем secret token
        const secretToken = request.headers.get('X-Telegram-Bot-Api-Secret-Token');
        if (secretToken !== token) {
          console.warn(`⚠️ Неверный токен: ${secretToken}`);
          return new Response(JSON.stringify({ ok: false, error: "Invalid token" }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        // Отправляем update на Python backend
        const backendResponse = await fetch(`${pythonBackend}/webhook`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Bot-Api-Secret-Token': token,
          },
          body: JSON.stringify(update),
        });

        // Проверяем ответ от backend
        if (!backendResponse.ok) {
          const errorText = await backendResponse.text();
          console.error(`❌ Backend ошибка: ${backendResponse.status} - ${errorText}`);
          return new Response(
            JSON.stringify({ 
              ok: false, 
              error: `Backend error: ${backendResponse.status}`,
              details: errorText
            }),
            {
              status: backendResponse.status,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }

        const backendData = await backendResponse.json();
        console.log(`✅ Update #${updateId} успешно обработан`);

        return new Response(JSON.stringify({ ok: true, update_id: updateId }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });

      } catch (error) {
        console.error(`❌ Webhook ошибка: ${error.message}`);
        return new Response(JSON.stringify({ 
          ok: false, 
          error: error.message 
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // ============ HEALTH CHECK ============
    if (request.method === 'GET' && url.pathname === '/health') {
      return new Response(JSON.stringify({ 
        status: 'ok', 
        timestamp: new Date().toISOString(),
        worker: 'Cloudflare Worker'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // ============ ROOT ============
    if (request.method === 'GET' && url.pathname === '/') {
      return new Response(JSON.stringify({
        name: "Education Bot Cloudflare Worker",
        version: "1.0.0",
        status: "running",
        endpoints: {
          "POST /webhook": "Webhook handler from Telegram",
          "GET /health": "Health check"
        }
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // ============ 404 ============
    return new Response(JSON.stringify({ error: 'Not Found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
