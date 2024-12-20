const fs = require('node:fs')
const portfinder = require('portfinder')
const { spawn, execFile } = require('node:child_process')
const path = require('node:path')

const { currentInterpreter } = require('./interpreterList')
const { ctrlc } = require('ctrlc-windows')
const exitProcess = async (serverProcess) => {
	if (serverProcess !== null) {
		if (process.platform === 'win32') {
			ctrlc(serverProcess.pid)
		} else {
			serverProcess.kill('SIGINT')
		}
	}
}

let currentServerProcess = null
let currentPort = null
let currentFile = null
const spawnLocalServer = (port, file) => {
	console.assert(path.isAbsolute(file));

	currentPort = port
	currentFile = file
	fs.writeFileSync(path.join(__dirname, '.last_file').replace('app.asar', 'app.asar.unpacked'), currentFile);

	let interpreter = currentInterpreter()
	const backendPath = path.join(__dirname, "backend").replace("app.asar", "app.asar.unpacked")
	const frontendPath = path.join(__dirname, "frontend", "dist").replace("app.asar", "app.asar.unpacked")
	const extensionsPath = path.join(__dirname, "extensions").replace("app.asar", "app.asar.unpacked")

	const fileCwd = path.dirname(currentFile)
	const filename = path.basename(currentFile)

	let finishStartPromiseResolve = null
	let finishStartPromise = new Promise((resolve, reject) => {
		finishStartPromiseResolve = resolve
	})

	console.log(`create server with ${interpreter.location}`)
	currentServerProcess = spawn(interpreter.location, [path.join(__dirname, 'entry', 'run.py').replace("app.asar", "app.asar.unpacked"),
			filename ? filename : '',
			'--cwd', fileCwd,
			'--backend-path', backendPath, 
			'--frontend-path', frontendPath, 
			'--extensions-path', extensionsPath, 
			'--port', `${port}`, 
			'--host', 'localhost',
		]
	)
	currentServerProcess.stdout.on('data', (data) => {
		// somehow the Unicorn running message comes out from stderr, I don't know
		console.log(`out get ${data}`)
		if (data.includes("Uvicorn running")) {
			finishStartPromiseResolve()
		}
	})
	currentServerProcess.stderr.on('data', (data) => {
		// somehow the Unicorn running message comes out from stderr, I don't know
		console.log(`err get ${data}`)
		if (data.includes("Uvicorn running")) {
			finishStartPromiseResolve()
		}
	})
	currentServerProcess.on('exit', onServerExit)
	return finishStartPromise
}

let respawn = false
function onServerExit(code) {
	if (respawn) {
		respawn = false
		spawnLocalServer(currentPort, currentFile)
		return
	}

	let exitMessagePath = path.join(__dirname, "entry", "_grapycal_open_another_workspace.txt").replace('app.asar', 'app.asar.unpacked');
	if (!fs.existsSync(exitMessagePath)) {
		currentPort = null
		currentFile = null
		currentServerProcess = null
		return 
	}

	let content = fs.readFileSync(exitMessagePath, 'utf8')
	fs.rmSync(exitMessagePath)
	let arg = content.split('\n')[0]
	spawnLocalServer(currentPort, path.resolve(path.dirname(currentFile), arg))
}

// there's a forward reference in onServerExit, so we use function here
const spawnServerAutoPort = async (file, onNoFreePortErr) => {
	try {
		var port = await portfinder.getPortPromise()
	} catch (noFreePortErr) {
		onNoFreePortErr(noFreePortErr)
		return
	}
	await spawnLocalServer(port, file)
	return port
}

// kill current server and spawn new server at same port with same file
// the only difference is that the interpreter might be changed by user
let respawnServerSameFileSamePort = () => {
	respawn = true
	exitProcess(currentServerProcess)
}

let exitCurrentServer = () => {
	respawn = false
	exitProcess(currentServerProcess)
}

module.exports = { spawnServerAutoPort, respawnServerSameFileSamePort, exitCurrentServer }