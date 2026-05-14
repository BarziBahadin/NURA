export default {
  root: '.',
  server: {
    port: 9000,
    proxy: {
      '/v1': 'http://localhost:8080',
    },
  },
}
