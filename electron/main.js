if (require('electron-squirrel-startup')) return;

const { app, BrowserWindow, Menu, dialog, MenuItem } = require('electron/main')
const path = require('node:path')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const ProgressBar = require('electron-progressbar')

const { interpreterList, addInterpreter, select, currentInterpreter } = require('./interpreterList')
const { spawnServerAutoPort, respawnServerSameFileSamePort, exitCurrentServer } = require('./serverManager')

const menuTemplate = () => [
	...(process.platform === 'darwin' ? 
	[{
		label: app.name,
		submenu: [
			{ role: "about" }
		]
	}] : []),
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
		title: "Python Interpreter",
		message: "Choose Python Interpreter",
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
const installGrapycal = async (pythonPath) => {
	const spawn = require('await-spawn') // overwrite the outer spawn
	const topicsyncPath = path.join(__dirname, "submodules", "topicsync").replace("app.asar", "app.asar.unpacked")
	const objectsyncPath = path.join(__dirname, "submodules", "objectsync").replace("app.asar", "app.asar.unpacked")
	const backendPath = path.join(__dirname, "backend").replace("app.asar", "app.asar.unpacked")
	const builtinExtensionPath = path.join(__dirname, "extensions", "grapycal_builtin").replace("app.asar", "app.asar.unpacked")
	const torchExtensionPath = path.join(__dirname, "extensions", "grapycal_torch").replace('app.asar', 'app.asar.unpacked')
	const installPaths = [topicsyncPath, objectsyncPath, backendPath, builtinExtensionPath, torchExtensionPath]

	var installProgress = new ProgressBar({
		indeterminate: false,
		text: 'Installing Grapycal',
		maxValue: installPaths.length
	});

	installProgress.on('completed', function() {
		installProgress.close()
	}).on('progress', function(value) {
		installProgress.detail = `Installing: ${value} out of ${installPaths.length} packages`
	});

	for (let packagePath of installPaths) {
		installProgress.value += 1
		await spawn(pythonPath, [
			'-m', 'pip', 'install', packagePath
		])
	}
}

const syncInterpreterListWithMenu = () => {
	let template = menuTemplate()
	template.at(-1).submenu = interpreterList()
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
		// fullscreen: true
		width: 800,
		height: 600
	})

	syncInterpreterListWithMenu()
	app.setAboutPanelOptions({
		applicationName: 'Grapycal', 
		applicationVersion: '0.18.4',
		copyright: 'Grapycal Team',
		iconPath: path.join(__dirname, 'frontend', 'dist', 'icon.png').replace("app.asar", "app.asar.unpacked")
	})
	win.loadURL(`http://localhost:${port}`)
	// win.webContents.openDevTools()
}

const quitApp = () => {
	exitCurrentServer()
	app.quit()
}

let mainWindowOpened = false
app.whenReady().then(async () => {
	if (!currentInterpreter()) {
		let interpreterPath = null 
		while(!interpreterPath) {
			interpreterPath = showSelectInterpreterDialog(null)
		}

		addInterpreter(interpreterPath)
		select(interpreterPath)
		await installGrapycal(interpreterPath)
	}

	let filePath = fs.readFileSync(path.join(__dirname, '.last_file').replace('app.asar', 'app.asar.unpacked'), 'utf8')
	while (!filePath) {
		// first time, asking where to save the file
		filePath = dialog.showSaveDialogSync({
			title: 'Create New File',
			filters: [{
		      name: 'Grapycal Workspace',
		      extensions: ['grapycal']
		    }],
			properties: ['createDirectory']
		})
		if (filePath === '') {
			// user cancel the dialog
			dialog.showMessageBoxSync({
				title: "Please choose your file location",
				message: "We need to know where you want to save the file"
			})
		}
	}

	let port = await spawnServerAutoPort(filePath, (noFreePortErr) => {
		// don't have error handling currently
		throw noFreePortErr
	})
	// await new Promise(resolve => setTimeout(resolve, 10000))
	createWindow(port)
	mainWindowOpened = true
	app.on('activate', () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow(port)
		}
	})
})

app.on('window-all-closed', () => {
	if (mainWindowOpened) {
		quitApp()
	}
})