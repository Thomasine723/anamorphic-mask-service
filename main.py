import io

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/apply-mask")
async def apply_mask(
    generated_image: UploadFile = File(...),
    mask: UploadFile = File(...)
):
    try:
        generated_bytes = await generated_image.read()
        mask_bytes = await mask.read()

        generated = Image.open(io.BytesIO(generated_bytes)).convert("RGB")
        bw_mask = Image.open(io.BytesIO(mask_bytes)).convert("L")

        if generated.size != bw_mask.size:
            raise HTTPException(
                status_code=400,
                detail="Generated image and mask must have identical pixel dimensions."
            )

        black_background = Image.new("RGB", generated.size, (0, 0, 0))

        final_image = Image.composite(
            generated,
            black_background,
            bw_mask
        )

        output = io.BytesIO()
        final_image.save(output, format="PNG")
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="image/png"
        )

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to process images: {str(error)}"
        )
