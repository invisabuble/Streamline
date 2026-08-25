console.log("Streamline.js loaded!");

const host = "http://streamline.local:8080"

// Get the list of devices from the backend.
async function get_devices() {
    const devices = await fetch(`${host}/api/devices`);
    return devices
}

console.log(get_devices());