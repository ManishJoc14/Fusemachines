# Week 11: Computer Vision with Deep Learning

These notes summarize the main ideas and implementations in the Week 11 assignment. The examples use CIFAR-10, PyTorch, and `torchvision`.

## 1. CNN foundations and image classification

### Convolution output size

For one spatial dimension:

$$
W_{out} = \left\lfloor\frac{W_{in}-K+2P}{S}\right\rfloor+1
$$

where $W_{in}$ is the input size, $K$ the kernel size, $P$ the padding, and $S$ the stride. Apply the same formula independently to height and width.

| Input | Kernel | Padding | Stride | Output |
|---:|---:|---:|---:|---:|
| 32 | 3 | 1 | 1 | 32 |
| 32 | 3 | 0 | 1 | 30 |
| 32 | 5 | 2 | 1 | 32 |
| 224 | 7 | 3 | 2 | 112 |
| 112 | 3 | 1 | 2 | 56 |

Padding of $(K-1)/2$ with an odd kernel and stride 1 preserves spatial size. A stride of 2 approximately halves it.

### Transfer learning with ResNet-50

Transfer learning reuses features learned from a large dataset such as ImageNet. For CIFAR-10:

1. Resize each `32 x 32` image to `224 x 224`.
2. Convert it to a tensor.
3. Normalize it using the ImageNet channel statistics:
   - mean: `[0.485, 0.456, 0.406]`
   - standard deviation: `[0.229, 0.224, 0.225]`
4. Load the pretrained ResNet-50.
5. Freeze the backbone with `requires_grad = False`.
6. Replace the original `2048 -> 1000` head with `nn.Linear(2048, 10)`.
7. Optimize only the new classification head.

The new head has $2048 \times 10 + 10 = 20,490$ trainable parameters. The assignment run obtained about **74.9% validation accuracy** after three epochs, an improvement of **29.9 percentage points** over the 45% HSV baseline.

Core training sequence:

```python
model.train()
optimizer.zero_grad()
logits = model(images)
loss = criterion(logits, labels)
loss.backward()
optimizer.step()
```

For validation, use `model.eval()` and `torch.no_grad()` so batch normalization behaves consistently and gradients are not stored.

### Grad-CAM

Grad-CAM explains a CNN prediction by highlighting spatial regions that positively influenced a selected class score.

1. Save the activations $A^k$ from a late convolutional layer with a forward hook.
2. Backpropagate the selected class score and save its gradients.
3. Globally average each channel's gradients:

$$
\alpha_k = \frac{1}{HW}\sum_i\sum_j \frac{\partial y^c}{\partial A_{ij}^k}
$$

4. Weight and sum the activation maps, then keep positive evidence:

$$
L_{GradCAM}^{c} = ReLU\left(\sum_k \alpha_k A^k\right)
$$

5. Normalize and resize the heatmap for display over the input.

Grad-CAM can reveal shortcut learning. For example, a model may focus on blue background resembling water and predict “ship” instead of attending to an airplane's shape.

## 2. Object detection

Image classification predicts one label for an image. Object detection predicts multiple bounding boxes, class labels, and confidence scores.

### Intersection over Union (IoU)

For boxes in `[x1, y1, x2, y2]` format:

$$
IoU(A,B) = \frac{|A \cap B|}{|A \cup B|}
$$

Implementation outline:

```python
inter_x1 = max(a[0], b[0])
inter_y1 = max(a[1], b[1])
inter_x2 = min(a[2], b[2])
inter_y2 = min(a[3], b[3])

inter_w = max(0, inter_x2 - inter_x1)
inter_h = max(0, inter_y2 - inter_y1)
intersection = inter_w * inter_h

area_a = (a[2] - a[0]) * (a[3] - a[1])
area_b = (b[2] - b[0]) * (b[3] - b[1])
union = area_a + area_b - intersection
iou = intersection / (union + 1e-6)
```

IoU is 0 for non-overlapping boxes and approximately 1 for identical boxes. For `[10,20,50,80]` and `[30,40,70,100]`, the intersection is 800, the union is 4,000, and the IoU is **0.20**.

### Faster R-CNN

Faster R-CNN is a two-stage detector:

1. A convolutional backbone extracts a feature map.
2. The Region Proposal Network proposes likely object regions using anchors, objectness scores, and box offsets.
3. RoI features are classified and their boxes refined.
4. Non-Maximum Suppression removes duplicate detections.

For `torchvision` inference, set the model to evaluation mode and pass a **list of image tensors**, not one stacked tensor:

```python
model.eval()
with torch.no_grad():
    output = model([image_tensor])[0]
```

The assignment detected 5 objects in the bus image and 3 in the people image at a 0.5 confidence threshold. A two-stage detector is a good choice when localization of small or overlapping objects matters more than maximum throughput; a one-stage model such as YOLO is often preferred when speed is the priority.

### Non-Maximum Suppression (NMS)

NMS removes multiple predictions for the same object:

1. Sort boxes by confidence from highest to lowest.
2. Keep the highest-scoring remaining box.
3. Remove remaining boxes whose IoU with it is at or above the threshold.
4. Repeat until no boxes remain.

A lower IoU threshold suppresses more boxes. Standard NMS is normally applied separately per class so overlapping objects from different classes do not suppress each other.

## 3. Image segmentation

### Semantic and instance segmentation

- **Semantic segmentation** assigns a class to every pixel but merges objects of the same class.
- **Instance segmentation** produces a separate mask for every object instance.

Instance segmentation is necessary for tasks such as counting two touching boxes of the same SKU; semantic segmentation may merge them into one region.

### DeepLabV3 inference

The segmentation model returns per-class logits with shape `(B, C, H, W)`. The predicted mask is the highest-scoring class at each pixel:

```python
with torch.no_grad():
    logits = model(x)["out"]
    mask = logits.argmax(dim=1)
```

The assignment images produced these classes:

- Bus image: background, bus, car, person
- People image: background, person

### Segmentation metrics

Pixel accuracy is easy to interpret but can be misleading when the background dominates:

$$
PixelAccuracy = \frac{\text{correctly classified pixels}}{\text{all pixels}}
$$

Class IoU is:

$$
IoU_c = \frac{|Pred_c \cap True_c|}{|Pred_c \cup True_c|}
$$

Mean IoU averages class IoUs, commonly across classes present in the ground truth:

$$
mIoU = \frac{1}{N}\sum_c IoU_c
$$

Always state how absent classes and ignore labels are handled because evaluation conventions differ.

### U-Net

U-Net combines a contracting encoder with a symmetric expanding decoder:

```text
Input
  -> [Conv, Conv] -> Pool --------------------------> Skip 1
      -> [Conv, Conv] -> Pool ----------------------> Skip 2
          -> [Conv, Conv] -> Pool ------------------> Skip 3
              -> [Conv, Conv] -> Pool --------------> Skip 4
                  -> [Conv, Conv] Bottleneck
              <- UpConv + Skip 4 -> [Conv, Conv]
          <- UpConv + Skip 3 -> [Conv, Conv]
      <- UpConv + Skip 2 -> [Conv, Conv]
  <- UpConv + Skip 1 -> [Conv, Conv] -> 1x1 class logits
```

Four pooling operations reduce the bottleneck to $1/16$ of the original spatial resolution. Skip connections copy high-resolution encoder features into the decoder, restoring edges and spatial detail lost during pooling. Without them, masks tend to have poorly localized boundaries.

Classical morphology can still be useful after segmentation. Opening removes isolated noise, while closing fills small gaps or holes cheaply and deterministically.

## 4. Variational Autoencoders (VAEs)

A VAE learns a probabilistic latent representation rather than mapping an image to a single fixed code.

### Architecture

- Encoder: strided convolutions reduce `3 x 32 x 32` to a feature vector.
- Two heads predict latent mean $\mu$ and log variance $\log\sigma^2$.
- Decoder: a linear projection followed by transposed convolutions reconstructs the image.
- A sigmoid output is appropriate when pixels are scaled to `[0, 1]`.

### Reparameterization trick

Direct sampling blocks ordinary backpropagation. Rewrite the sample as:

$$
\sigma = \exp(0.5\log\sigma^2), \qquad
\epsilon \sim \mathcal{N}(0,I), \qquad
z = \mu + \sigma \odot \epsilon
$$

Randomness now enters through $\epsilon$, while $z$ remains differentiable with respect to $\mu$ and $\sigma$.

### VAE objective

The loss balances reconstruction quality and latent regularity:

$$
\mathcal{L} = \mathcal{L}_{recon} + \beta D_{KL}\left(q(z|x)\;||\;\mathcal{N}(0,I)\right)
$$

For a diagonal Gaussian:

$$
D_{KL} = -\frac{1}{2}\sum_j\left(1+\log\sigma_j^2-\mu_j^2-\sigma_j^2\right)
$$

The notebook sums reconstruction MSE over pixels for each image and then averages over the batch. Using a global mean changes the scale drastically and can let the KL term dominate.

The recorded epoch-3 values were reconstruction loss **74.4604** and KL divergence **351.04**. MSE-trained reconstructions are often blurry because averaging several plausible pixel values minimizes squared error. Smooth latent interpolation indicates that nearby latent points decode to visually similar images.

A VAE may augment a small dataset by fine-tuning on the target class, encoding real examples, sampling near their latent distributions or interpolating between codes, decoding new images, and quality-checking the generated samples. Synthetic data should be validated because unrealistic samples can harm a classifier.

## 5. Vision Transformers, CLIP, and deployment

### ViT patch embeddings

An image is split into non-overlapping patches and each patch becomes a token. A convolution with `kernel_size == stride == patch_size` performs patch extraction and learned projection efficiently.

For a `32 x 32` image with `4 x 4` patches:

$$
N = (32/4)^2 = 64\text{ patches}
$$

With a prepended classification token, the sequence length is 65. With embedding size 256, the output shape for batch size $B$ is `(B, 65, 256)`. Positional embeddings are added because self-attention alone does not encode patch order.

### CLIP zero-shot classification

CLIP maps images and text into one embedding space:

1. Create prompts such as `"a photo of a ship"`.
2. Encode and L2-normalize each text embedding.
3. Encode and L2-normalize an image embedding.
4. Compute image-text dot products; after normalization these are cosine similarities.
5. Choose the prompt with the largest similarity.

Prompt wording matters because it changes the text embedding. The assignment reports about **92%** on its 200-image zero-shot sample, but this small-sample result should not be treated as a stable production benchmark.

### ONNX export checklist

1. Put the model in `eval()` mode.
2. Move the model and dummy input to the same device, usually CPU for export.
3. Use a dummy tensor with the expected shape, here `(1, 3, 224, 224)`.
4. Name inputs and outputs.
5. Declare the batch dimension dynamic if variable batch sizes are needed.
6. Export with a supported opset, such as 17.
7. Load the artifact with ONNX Runtime and verify that output shape is `(B, 10)`.

Exporting does not validate predictive equivalence by itself. For stronger verification, compare PyTorch and ONNX logits on the same inputs within a numerical tolerance.

## Model selection summary

| Model | Assignment accuracy | Main strength | Main limitation | Suitable role |
|---|---:|---|---|---|
| HSV rules | ~45% | Extremely fast and simple | Brittle; rules must be rewritten | Narrow, controlled baseline |
| Fine-tuned ResNet-50 | ~75% | Good speed/accuracy balance; Grad-CAM | Needs labeled examples for new classes | Primary classifier |
| CLIP zero-shot | ~92% on 200 samples | Adds classes using text prompts | Higher latency; benchmark needs broader validation | Rapid class onboarding |
| VAE | Not a classifier | Learns a generative latent space | Blurry output and no direct class decision | Data augmentation/reconstruction |

For a multi-camera warehouse system, a practical design is to serve the fine-tuned classifier through ONNX for routine inference, use CLIP selectively to explore or onboard new categories, and keep the VAE offline for data augmentation. Detection or instance segmentation is still required when the system must locate and count multiple objects rather than assign one label to an entire frame.

## Common pitfalls

- Forgetting ImageNet normalization when using pretrained ImageNet classifiers.
- Updating all pretrained weights when the intention is to train only the new head.
- Running validation without `model.eval()` or accidentally retaining gradients.
- Passing a stacked batch tensor to a `torchvision` detection model instead of a list of tensors.
- Forgetting to clamp intersection width and height to zero in IoU.
- Applying NMS across classes rather than within each class.
- Trusting pixel accuracy alone on class-imbalanced segmentation data.
- Averaging VAE reconstruction loss over every pixel without retuning $\beta$.
- Exporting to ONNX without checking inference in ONNX Runtime.
- Comparing latency numbers without fixing hardware, batch size, image size, precision, and warm-up conditions.
