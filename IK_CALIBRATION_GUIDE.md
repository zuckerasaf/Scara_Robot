# Inverse Kinematics Calibration Guide

## Problem Analysis

Your IK calculations are producing incorrect positions. Based on your data:

| Command (X,Y) | Real Position (X,Y) | Error (X,Y) |
|---------------|---------------------|-------------|
| (10, 10) | (-7.5, 13) | (-17.5, +3) |
| (5, 5) | (-2.7, 16.5) | (-7.7, +11.5) |
| (7.5, 15) | (-7.8, 12.8) | (-15.3, -2.2) |
| (-5, 3) | (2.4, 19.6) | (+7.4, +16.6) |

## Root Causes

### 1. **Zero Position Mismatch** (MOST LIKELY)
The "Go to Zero" position (Y=-8000, X=3545, Z=-4927, A=-250 steps) does NOT correspond to (0,0) in the IK coordinate system.

**Current IK assumption:** (0,0) = end effector at fully extended down position  
**Reality:** After go_to_zero(), the end effector is at some OTHER physical position

### 2. **Step Direction Issues**
The +/- direction of steps might be inverted compared to the IK calculations.

### 3. **Arm Length Inaccuracy**
L1 and L2 values (25cm, 15cm) might not match the actual physical robot.

## Calibration Steps

### Step 1: Measure Actual Arm Lengths
**Physically measure:**
- L1 (shoulder to elbow joint): _____ cm
- L2 (elbow to end effector): _____ cm

Update in `axis_config.json`:
```json
"robot_geometry": {
    "arm_link_1_length_cm": <measured_L1>,
    "arm_link_2_length_cm": <measured_L2>
}
```

### Step 2: Determine True Zero Position
After running "Go to Zero", measure where the end effector actually is:

1. Run "Home" then "Go to Zero"
2. **Physically measure** from the base joint center:
   - Horizontal distance (X): _____ cm (+ = right, - = left)
   - Vertical distance (Y): _____ cm (+ = up, - = down)

This is your **zero offset**.

### Step 3: Test Step Directions
From zero position, manually command:
- X +1000 steps → Does arm rotate CW (+) or CCW (-)? _____
- Z +1000 steps → Does elbow rotate CW (+) or CCW (-)? _____

### Step 4: Fix IK Calculation

Based on your measurements, you need to modify the IK calculation to:
1. Add the zero position offset
2. Correct step direction signs  
3. Use accurate arm lengths

## Expected Fix

The `inverse_kinematics()` function needs:

```python
# Add measured zero position offset
zero_offset_x = <measured_value>  # cm
zero_offset_y = <measured_value>  # cm

# Transform user coordinates accounting for zero offset
x_base = target_x_cm - zero_offset_x
y_base = (target_y_cm - zero_offset_y) - (L1 + L2)

# Possibly invert step signs if directions are wrong
x_steps = int(theta1_robot_deg * x_steps_per_deg) * direction_sign_x
z_steps = int(theta2_deg * z_steps_per_deg) * direction_sign_z
```

## Quick Test

After calibration, test with a simple position:
- Command: (0, 0) → Should return to zero position exactly
- Command: (10, 0) → Should move 10cm to the right
- Command: (0, 10) → Should move 10cm up

## Fill in Your Measurements

1. Measured L1 = **22.8 cm** ✓ (from HowToMechatronics design)
2. Measured L2 = **13.65 cm** ✓ (from HowToMechatronics design)
3. Zero position X offset = **0 cm** ✓ (end effector centered)
4. Zero position Y offset = **~0.45 cm** ✓ (36 cm measured vs 36.45 cm theoretical = negligible)
5. X step direction: **-1000 steps → CCW** (positive steps = CW)
6. Z step direction: **-1000 steps → CCW** (positive steps = CW)

## Calibration Applied ✅
- ✅ Arm lengths corrected: L1=22.8cm, L2=13.65cm
- ✅ **Coordinate System Transform Added** (CRITICAL FIX):
  - **User coordinates** = from user perspective sitting in front of robot
    - Origin at Zero_point (end effector at zero configuration)
    - +X = user's right (robot's left)
    - +Y = toward user (closer than zero position)
  - **Base coordinates** = origin at shoulder joint (for IK calculations)
  - **Zero_point** = (0, 36.45cm) in base coordinates
  - **Transform**:
    - x_base = -x_user (mirror X axis)
    - y_base = 36.45 - y_user (invert Y axis)
  - **Example**: User (-10, 10) → Base (+10, 26.45) → IK calculates angles
- ✅ Zero position nearly perfect (offset < 0.5 cm)
- ✅ X direction inverted in IK calculation (multiplied by -1)
- ✅ Step directions confirmed: +steps=CW, -steps=CCW

## Next: Test IK Accuracy
Now test the IK with actual positions and measure results!
