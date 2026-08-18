import io
import numpy as np
import cv2

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from PIL import Image

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/apply-mask",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Masked PNG image"
        }
    }
)
async def apply_mask(
    generated_image: UploadFile = File(...),
    mask: UploadFile = File(...)
):
    try:
        generated_bytes = await generated_image.read()
        mask_bytes = await mask.read()

        generated = Image.open(
            io.BytesIO(generated_bytes)
        ).convert("RGB")

        bw_mask = Image.open(
            io.BytesIO(mask_bytes)
        ).convert("L")

        if generated.size != bw_mask.size:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Generated image and mask must have "
                    "identical pixel dimensions."
                )
            )

        black_background = Image.new(
            "RGB",
            generated.size,
            (0, 0, 0)
        )

        final_image = Image.composite(
            generated,
            black_background,
            bw_mask
        )

        output = io.BytesIO()
        final_image.save(output, format="PNG")

        return Response(
            content=output.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition":
                "attachment; filename=masked-output.png"
            }
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to process images: {str(error)}"
        )


@app.post(
    "/make-safe-zone",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Safe-zone PNG image"
        }
    }
)
async def make_safe_zone(
    mask: UploadFile = File(...)
):
    try:
        mask_bytes = await mask.read()

        original_mask = Image.open(
            io.BytesIO(mask_bytes)
        ).convert("L")

        # Convert the original mask to pure black and white.
        binary_mask = np.array(original_mask)

        binary_mask = np.where(
            binary_mask >= 128,
            255,
            0
        ).astype(np.uint8)

        # Calculate each white pixel's distance
        # from the nearest black pixel.
        distance = cv2.distanceTransform(
            binary_mask,
            cv2.DIST_L2,
            5
        )

        # Hero content should remain at least
        # 80 pixels inside the original boundary.
        radius = 80

        safe_array = np.where(
            distance >= radius,
            255,
            0
        ).astype(np.uint8)

        safe_zone = Image.fromarray(
            safe_array
        )

        output = io.BytesIO()
        safe_zone.save(
            output,
            format="PNG"
        )

        return Response(
            content=output.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition":
                "attachment; filename=safe-zone.png"
            }
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to create safe zone: {str(error)}"
        )
