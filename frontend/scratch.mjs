import * as stdb from 'spacetimedb';

console.log(Object.keys(stdb));

const client = new stdb.SpacetimeDBClient("http://127.0.0.1:3000");
console.log(Object.keys(client));
