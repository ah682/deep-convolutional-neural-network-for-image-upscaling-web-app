function activateDyslexiaAssist() {
  document.body.classList.toggle("dyslexia-mode");
}

// Prevent the default anchor behavior
function setColorBlindMode(mode, event) {
  event.preventDefault();

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
