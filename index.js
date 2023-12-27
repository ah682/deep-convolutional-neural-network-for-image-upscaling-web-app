document.querySelector('.upload-button').addEventListener('click', function() {
  document.getElementById('hiddenFileInput').click();
});

function handleFileUpload(input) {
  if (input.files && input.files[0]) {
      // Handle the file upload here, e.g., display the file name or upload it
      console.log("File Uploaded: ", input.files[0].name);
      // Additional actions upon file selection
  }
}
