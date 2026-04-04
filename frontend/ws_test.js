const http = require('http');

http.get('http://127.0.0.1:3000/v1/database/realitypatch-db-2lsay/subscription', res => {
  console.log('/subscription HTTP status:', res.statusCode);
});

http.get('http://127.0.0.1:3000/v1/database/realitypatch-db-2lsay/subscribe', res => {
  console.log('/subscribe HTTP status:', res.statusCode);
});

http.get('http://127.0.0.1:3000/database/realitypatch-db-2lsay/subscription', res => {
  console.log('no v1 /subscription HTTP status:', res.statusCode);
});
