import logo from './logo.svg';
import './App.css';
import { useState } from 'react';

function App() {

  const [response, setResponse] = useState("")

  const testApi = () => {
    fetch("/api")
    .then((res) => {
      if (res.ok) {
        return res.json()
      }
    })
    .then((data) => {
      setResponse(data.message)
    })
  }

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
        change!
          <button onClick={testApi}>Test API</button>
          API response: {response}
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

export default App;
