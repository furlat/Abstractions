# Research Proposal: Learning Modular Sprite Decomposition Through Geometric-Semantic Disentanglement

## Abstract

This project proposes a novel approach to automatically decompose 2D character sprites into their constituent modular components (heads, torsos, weapons, etc.) using deep learning. We introduce two complementary architectures: (1) a multi-head perceptron with explicit geometric constraints, and (2) a VQ-VAE with learned latent disentanglement. The key innovation lies in leveraging both supervised component prediction and unsupervised circular reconstruction loss for robust evaluation on unlabeled data.

## 1. Problem Statement & Motivation

Modern 2D game development relies heavily on modular character systems where artists combine interchangeable parts (heads, armor, weapons) to create diverse characters. However, existing sprites are often monolithic - making it impossible to mix-and-match components from different art sources. 

**Research Question**: Can we learn to reverse-engineer complete character sprites back into their modular components, enabling automatic conversion of any sprite into a modular system?

## 2. Forward Process: Component Assembly

### 2.1 Sprite Generation Pipeline
We assume access to a deterministic sprite assembly system that combines modular components:

```
Components = {head_type, chest_type, legs_type, weapon_type, colors, ...}
Assembly_Function(Components, Direction) → 128×128 Sprite
```

This forward process generates 8-directional sprites (N, NE, E, SE, S, SW, W, NW) from the same component configuration, providing natural data augmentation and geometric consistency constraints.

### 2.2 Deterministic Component Stitching
The assembly process follows strict layering rules:
- **Background → Legs → Torso → Arms → Head → Accessories**
- Each component has predefined anchor points and z-ordering
- Color palettes are applied consistently across directions
- Occlusion patterns are deterministic based on viewing angle

## 3. Architecture 1: Multi-Head Perceptron with Geometric Equivariance

### 3.1 Shared Latent Space Design
```
8 Direction Images → Shared Encoder → Component Latent Space
                                    ↓
Direction-Specific Heads → Component Predictions
```

**Key Insight**: All 8 directional views represent the same character composition - only the viewing angle changes. This provides a natural constraint for learning direction-invariant semantic features.

### 3.2 Training Strategy
Each training sample consists of 8 directional images with identical ground-truth components:

```python
Sample = {
    'images': [North, NE, East, SE, South, SW, West, NW],  # 8×128×128×3
    'components': [head_id, chest_id, weapon_id, ...]      # Same for all 8!
}
```

**Loss Function**:
```python
L_supervised = Σ(direction=1 to 8) CrossEntropy(pred_components[direction], true_components)
```

This creates strong geometric equivariance constraints - the model must predict identical components regardless of viewing direction.

## 4. Architecture 2: VQ-VAE with Learned Disentanglement

### 4.1 Factorized Latent Space
```python
z_semantic = VQ_Codebook_Semantic(semantic_features)    # What components
z_direction = VQ_Codebook_Direction(direction_features)  # How oriented
```

### 4.2 Disentanglement Through Constraints
- **Semantic codes** must be identical across all 8 directions of the same character
- **Direction codes** should be predictable from viewing angle alone
- **Compositional generation**: Any semantic code + any direction code = valid sprite

### 4.3 Advanced Capabilities
Once trained, the model enables:
- **Single-direction inference**: Front view → All 8 directions
- **Interpolated directions**: Generate 16/24 viewing angles through code interpolation
- **Component mixing**: Combine semantic codes from different characters

## 5. Evaluation: Circular Loss for Unlabeled Data

### 5.1 The Challenge
While we have supervised training data, we want to evaluate on real artist sprites without known component labels.

### 5.2 Circular Loss Methodology
```
Unknown Sprite → [Trained Model] → Predicted Components
                                        ↓
                [Assembly System] → Reconstructed Sprite
                                        ↓
                L_circular = ||Original - Reconstructed||₁
```

**Key Advantage**: This requires no ground-truth labels yet provides meaningful evaluation of decomposition quality.

### 5.3 Perfect Reconstruction Feasibility
Since we work with 128×128 pixel art:
- **Discrete color palettes** → Exact color matching possible
- **Sharp pixel boundaries** → L₁ loss can theoretically reach 0
- **Fixed resolution** → Finite complexity space

## 6. Methodology & Implementation Plan

### Phase 1: Data Generation & Baseline (Months 1-2)
- Generate diverse training dataset using modular sprite system
- Implement multi-head perceptron architecture
- Establish supervised training pipeline and evaluation metrics

### Phase 2: Advanced Architecture (Months 3-4)
- Develop VQ-VAE with factorized latent space
- Implement equivariance constraints and disentanglement losses
- Compare architectures on supervised benchmarks

### Phase 3: Evaluation & Transfer (Months 5-6)
- Implement circular loss evaluation framework
- Test on unlabeled artist sprites from different styles
- Analyze generalization capabilities and failure modes

## 7. Expected Contributions

1. **Novel architecture** for sprite decomposition with geometric constraints
2. **Circular loss framework** for evaluation without labels
3. **Disentangled representation learning** for compositional sprite generation
4. **Practical tool** for game developers to convert legacy sprites to modular systems

## 8. Technical Challenges & Mitigation

### 8.1 Occlusion Handling
**Challenge**: Some components may be hidden in certain directions
**Solution**: Predict component presence confidence alongside component type

### 8.2 Art Style Generalization  
**Challenge**: Training data from one art style may not transfer
**Solution**: Circular loss evaluation on diverse art styles + domain adaptation techniques

### 8.3 Component Granularity
**Challenge**: Defining optimal component decomposition level
**Solution**: Hierarchical decomposition with multiple granularity levels

## 9. Success Metrics

- **Supervised Accuracy**: Component prediction accuracy on labeled test set
- **Circular Loss**: Reconstruction quality on unlabeled sprites (target: <5% pixel error)
- **Human Evaluation**: Artist assessment of decomposition quality and utility
- **Generalization**: Performance across different art styles and resolutions

## 10. Timeline & Resources

**Duration**: 6 months  
**Computational Requirements**: GPU with 8GB+ VRAM for training  
**Expected Outcome**: Working prototype + research paper submission

This project combines fundamental research in disentangled representation learning with practical applications in game development, making it an ideal thesis topic that bridges theory and application.