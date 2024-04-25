const { app, BrowserWindow } = require('electron/main')
const { spawn } = require('node:child_process')
const portfinder = require('portfinder')
const { ctrlc } = require('ctrlc-windows')
const fs = require('node:fs')

const createWindow = (port) => {
  const win = new BrowserWindow({
    fullscreen: true
  })

  win.loadURL(`http://localhost:${port}/frontend`)
  // win.webContents.openDevTools()
}

const quitApp = (serverProcess) => {
  if (serverProcess !== null) {
    if (process.platform === 'win32') {
      ctrlc(serverProcess.pid)
    } else {
      serverProcess.kill('SIGINT')
    }
  }

  app.quit()
}

const spawnLocalServer = (port, file) => {
  return spawn('python3.11', ['../entry/run.py', 
    file ? file : '',
    '--backend-path', '../backend', 
    '--frontend-path', '../frontend/dist', 
    '--extensions-path', '../extensions', 
    '--port', `${port}`, 
    '--host', 'localhost',
    ], 
  {
    shell: process.platform === 'win32',
    stdio: 'inherit' // so we can check the output of run.py
  })
}

let currentServerProcess = null;
const spawnServerAutoPort = async (file) => {
  try {
    var port = await portfinder.getPortPromise()
  } catch (noFreePortErr) {
    quitApp(currentServerProcess)
    return
  }

  return [spawnLocalServer(port, file), port]
}

const onServerExit = async (code) => {
  if (!fs.existsSync("grapycal_exit_message_")) {
    return 
  }

  let content = fs.readFileSync('grapycal_exit_message_', 'utf8')
  fs.rmSync("grapycal_exit_message_")
  let firstLine = content.split('\n')[0]
  let [op, arg] = firstLine.split(" ")
  if (op == 'open') {
    let [currentServerProcess, _] = await spawnServerAutoPort(arg)
    currentServerProcess.on('exit', onServerExit)
  }
}

app.whenReady().then(async () => {
  let [currentServerProcess, port] = await spawnServerAutoPort(null)
  currentServerProcess.on('exit', onServerExit)

  //wait for 2 seconds as we don't know how the process goes
  await new Promise(resolve => setTimeout(resolve, 2000))
  createWindow(port)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(port)
    }
  })
})

app.on('window-all-closed', () => {
  quitApp(currentServerProcess)
})