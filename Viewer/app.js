var express = require('express');
var app = express();
app.use('/', express.static(__dirname + '/html'));
app.listen(3000, function() { console.log('listening')});
