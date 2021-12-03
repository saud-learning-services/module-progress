const data = require("./permissions.json");

const length = data.courses.length;
const contentRange = "courses 0-" + length + "/" + length;

module.exports = (req, res, next) => {
  res.header("Content-Range", contentRange);
  next();
};
