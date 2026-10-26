const form = document.getElementById('upload-form');
const fileInput = document.getElementById('hiddenFileInput');
const status = document.getElementById('text-setter');
const uploadButton = document.getElementById('upload-button');
const images = document.getElementById('image-container');

async function showImages() {
  const response = await fetch('/get_images');
  if (!response.ok) throw new Error('Saved images could not be loaded.');
  const filenames = await response.json();
  images.replaceChildren();
  for (const filename of filenames) {
    const link = document.createElement('a');
    link.href = '/results/' + filename;
    const image = document.createElement('img');
    image.src = link.href;
    image.alt = 'Saved 4× ESRGAN result; open full image';
    image.style.maxWidth = '200px';
    link.append(image);
    images.append(link);
  }
}

uploadButton.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) form.requestSubmit();
});
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  uploadButton.disabled = true;
  status.textContent = 'Upscaling image…';
  try {
    const response = await fetch('/upload', { method: 'POST', body: new FormData(form) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Upload failed.');
    status.textContent = 'Upscaling complete. Open a result below to save it.';
    await showImages();
  } catch (error) {
    status.textContent = error.message || 'The local server could not be reached.';
  } finally {
    uploadButton.disabled = false;
    fileInput.value = '';
  }
});
document.getElementById('show-images-btn').addEventListener('click', async () => {
  try { await showImages(); }
  catch (error) { status.textContent = error.message; }
});
