console.log("Streamline.js loaded!");

const host = "http://streamline.local:8080"

// Get the list of devices from the backend.
async function get_route(route) {
    const response = await fetch(`${host}/api/${route}`);
    return await response.json()
}

// Main streamline method.
async function streamline () {

    // Get the devices and files from the API.
    const devices = await get_route("devices");
    const files   = await get_route("get_file_list");

    const selector = document.getElementById("devices");

    for (const [ip, device] of Object.entries(devices)) {
        const option = document.createElement("option");
        option.value = ip;
        option.textContent = device.device_info.friendlyName || ip;
        selector.appendChild(option);
    }

    for (const [entry, info] of Object.entries(files)) {
        console.log(entry, info);
    }

}

streamline();

