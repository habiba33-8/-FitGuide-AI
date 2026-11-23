/** Shrink a photo in the browser before upload (Vercel limits request size, and smaller images are faster for the model). */
export async function resizeToJpeg(file: File, maxSide = 1024, quality = 0.82): Promise<{ base64: string; dataUrl: string }> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  return { base64: dataUrl.split(",")[1], dataUrl };
}
