import { createApp } from "./app.js";

const port = process.env.PORT || 3000;
createApp().listen(port, () => console.log(`Photo to Table running on http://localhost:${port}`));
