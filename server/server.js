const express = require('express');
const app = express();
const port = 5000;

app.get("/api", (req, res) => {
    res.json({
        "message": "Successfully connected to backend"
    })
})

app.listen(port, () => {
    console.log(`API listening on port ${port}`)
})