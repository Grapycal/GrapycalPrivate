const { app, BrowserWindow, Menu, dialog, MenuItem } = require('electron/main')
const path = require('node:path')
const { spawn } = require('node:child_process')

const { interpreterList, addInterpreter, select, currentInterpreter } = require('./interpreterList')
const { spawnServerAutoPort, respawnServerSameFileSamePort, exitCurrentServer } = require('./serverManager')

const menuTemplate = () => [
	(process.platform === 'darwin' ? 
	{
		label: app.name,
		submenu: [
			{ role: "about" }
		]
	} : []),
	{
		label: "Interpreter", 
		submenu: [
		// { type: 'separator' },
		// { label: 'Add Python Interpreter...' }
		]
	}
]

const showSelectInterpreterDialog = (browserWindow) => {
	let paths = dialog.showOpenDialogSync(browserWindow, {
		properties: ["openFile", "showHiddenFiles"]
	})
	if (paths === undefined) {
		//canceled
		return undefined
	}

	let filePath = paths[0]
	if (path.basename(filePath).includes('python')) {
		return filePath
	}

	// error: invalid interpreter name, interpreter name should contains python substring
	dialog.showErrorBox("Select Python Interpreter", "Invalid Python interpreter name")
	return showSelectInterpreterDialog(browserWindow)
}

const selectInterpreter = (path) => {
	select(path)
	syncInterpreterListWithMenu()
	respawnServerSameFileSamePort()
}

const util = require('node:util');
const exec = util.promisify(require('node:child_process').exec);
const installGrapycal = async (path) => {
	const spawn = require('await-spawn') // overwrite the outer spawn
	await spawn(path, [
		'-m', 'pip', 'install', '../submodules/topicsync', '../submodules/objectsync', '../backend', '../extensions/grapycal_builtin'
	], 
	{
		stdio: 'inherit' // so we can check the output of run.py
	})
}

const syncInterpreterListWithMenu = () => {
	let template = menuTemplate()
	template[1].submenu = interpreterList()
		.map((item) => ({ 
			label: item.location, 
			type: 'radio', 
			checked: item.using,
			click: (item, browser, event) => {
				selectInterpreter(item.label)
			}
		}))
		.concat(
			[
				{ type: 'separator' }, 
				{ label: 'Add Python Interpreter...', click: async (item, browser, event) => {
					let filePath = showSelectInterpreterDialog(browser)
					if (filePath === undefined) {
						// canceled
						return
					}
					addInterpreter(filePath)

					await installGrapycal(filePath)
					selectInterpreter(filePath)
				}}
			]
		)

	const menu = Menu.buildFromTemplate(template)
	Menu.setApplicationMenu(menu)
}

const createWindow = (port) => {
	const win = new BrowserWindow({
		fullscreen: true
	})

	syncInterpreterListWithMenu()
	app.setAboutPanelOptions({
		applicationName: 'Grapycal', 
		applicationVersion: '0.11.3',
		copyright: 'Grapycal Team',
		iconPath: '../frontend/dist/icon.png'
	})

	win.loadURL(`http://localhost:${port}/frontend`)
	// win.webContents.openDevTools()
}

const quitApp = () => {
	exitCurrentServer()
	app.quit()
}


app.whenReady().then(async () => {
	let port = await spawnServerAutoPort(null, (noFreePortErr) => {
		// don't have error handling currently
	})

	//wait for 10 seconds as we don't know how the process goes
	await new Promise(resolve => setTimeout(resolve, 10000))
	createWindow(port)

	app.on('activate', () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow(port)
		}
	})
})

app.on('window-all-closed', () => {
	quitApp()
})