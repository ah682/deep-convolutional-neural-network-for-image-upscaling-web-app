function activateDyslexiaAssist() {
  // Add code here to toggle dyslexia-friendly styles
  document.body.classList.toggle("dyslexia-mode");

  // You can add more changes such as changing font, colors etc.
}

function setColorBlindMode(mode) {
  var bodyElement = document.body;
  // Clear all previous colorblind classes
  bodyElement.classList.remove(
    "no-color-blindness",
    "deuteranopia",
    "protanopia",
    "tritanopia",
    "monochromatism"
  );
  // Add the selected mode
  bodyElement.classList.add(mode);
}
