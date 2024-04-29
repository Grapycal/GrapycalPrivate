const fs = require('node:fs')
const portfinder = require('portfinder')
const { spawn } = require('node:child_process')

const { currentInterpreter } = require('./interpreterList')

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
	currentPort = port
	currentFile = file

	let interpreter = currentInterpreter()
	if (interpreter.location == 'builtin') {
		console.log('create builtin server')
		currentServerProcess = spawn('../basic_grapycal/run', [
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
	} else {
		console.log(`create server with ${interpreter.location}`)
		currentServerProcess = spawn(interpreter.location, ['../entry/run.py',
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
			}
		)
	}

	currentServerProcess.on('exit', onServerExit)
}

let respawn = false
function onServerExit(code) {
	if (respawn) {
		respawn = false
		spawnLocalServer(currentPort, currentFile)
		return
	}

	if (!fs.existsSync("grapycal_exit_message_")) {
		currentPort = null
		currentFile = null
		currentServerProcess = null
		return 
	}

	let content = fs.readFileSync('grapycal_exit_message_', 'utf8')
	fs.rmSync("grapycal_exit_message_")
	let firstLine = content.split('\n')[0]
	let [op, arg] = firstLine.split(" ")
	if (op == 'open') {
		spawnLocalServer(currentPort, arg)
	}
}

// there's a forward reference in onServerExit, so we use function here
const spawnServerAutoPort = async (file, onNoFreePortErr) => {
	try {
		var port = await portfinder.getPortPromise()
	} catch (noFreePortErr) {
		onNoFreePortErr(noFreePortErr)
		return
	}
	spawnLocalServer(port, file)
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