const express = require('express');
const app = express();
const port = 5000;

// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAce4YdcdP0LP39_IkQxGxD20tM3jkEIHw",
  authDomain: "simplefile-7c6a6.firebaseapp.com",
  projectId: "simplefile-7c6a6",
  storageBucket: "simplefile-7c6a6.appspot.com",
  messagingSenderId: "1010698599713",
  appId: "1:1010698599713:web:aeccffa21beeb5dbcfd260",
  measurementId: "G-QSFZR4G4DH"
};

// Initialize Firebase
const firebase = initializeApp(firebaseConfig);
const analytics = getAnalytics(firebase);

app.get("/api", (req, res) => {
    res.json({
        "message": "Successfully connected to backend"
    })
})

app.listen(port, () => {
    console.log(`API listening on port ${port}`)
})