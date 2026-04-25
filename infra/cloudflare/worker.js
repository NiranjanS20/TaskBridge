export default {
  async fetch(request) {
    return new Response("TaskBridge edge worker placeholder", {
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  },
};

