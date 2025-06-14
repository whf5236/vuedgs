import { crossProduct, dotProduct, normalizeVector } from './vector.js';

// ========== 3x3 矩阵运算 ==========
function multiplyMatrix3x3(a, b) {
  const result = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      for (let k = 0; k < 3; k++) {
        result[i][j] += a[i][k] * b[k][j];
      }
    }
  }
  return result;
}

function scaleMatrix3x3(m, s) {
  return m.map(row => row.map(val => val * s));
}

function addMatrix3x3(a, b) {
  const result = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      result[i][j] = a[i][j] + b[i][j];
    }
  }
  return result;
}

function multiplyMatrix3x3ByVector3(m, v) {
    const result = [0, 0, 0];
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
            result[i] += m[i][j] * v[j];
        }
    }
    return result;
}


/**
 * 核心：复现 Python `rotate_coordinates` 函数
 * 使用罗德里格旋转公式 (Rodrigues' rotation formula)
 * @param {number[]} coordinates 要旋转的坐标
 * @param {number[]} vector 目标 `up_vector`
 * @returns {number[]} 旋转后的坐标
 */
export function rotateCoordinates(coordinates, vector) {
  if (vector.every(v => v === 0)) {
    return coordinates;
  }
  const unit_vector = normalizeVector(vector);

  const base_vector = [0.0, -1.0, 0.0];
  const theta = Math.acos(dotProduct(unit_vector, base_vector));

  if (theta < 1e-5) {
      return coordinates; // 几乎没有旋转
  }

  if (Math.abs(theta - Math.PI) < 1e-5) {
      // 旋转180度
      return [-coordinates[0], -coordinates[1], coordinates[2]];
  }
  
  const k = normalizeVector(crossProduct(base_vector, unit_vector));
  
  const K = [
    [0, -k[2], k[1]],
    [k[2], 0, -k[0]],
    [-k[1], k[0], 0]
  ];
  
  const I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  
  const K_sin_theta = scaleMatrix3x3(K, Math.sin(theta));
  const K_squared = multiplyMatrix3x3(K, K);
  const K_sq_1_minus_cos_theta = scaleMatrix3x3(K_squared, 1 - Math.cos(theta));

  const rotation_matrix = addMatrix3x3(I, addMatrix3x3(K_sin_theta, K_sq_1_minus_cos_theta));

  return multiplyMatrix3x3ByVector3(rotation_matrix, coordinates);
}

// ========== 4x4 矩阵运算 ==========

/**
 * 将扁平矩阵转换为4x4二维数组
 * @param {number[]} flatMatrix
 * @returns {number[][]}
 */
export function to4x4(flatMatrix) {
  const m = [];
  for (let i = 0; i < 4; i++) {
    m[i] = [];
    for (let j = 0; j < 4; j++) {
      m[i][j] = flatMatrix[i * 4 + j];
    }
  }
  return m;
}

/**
 * 4x4矩阵乘法
 * @param {number[][]} a
 * @param {number[][]} b
 * @returns {number[][]}
 */
export function multiplyMatrices(a, b) {
  const result = [];
  for (let i = 0; i < 4; i++) {
    result[i] = [];
    for (let j = 0; j < 4; j++) {
      result[i][j] = 0;
      for (let k = 0; k < 4; k++) {
        result[i][j] += a[i][k] * b[k][j];
      }
    }
  }
  return result;
}

/**
 * 将4x4矩阵展平为16元素数组
 * @param {number[][]} matrix
 * @returns {number[]}
 */
export function flattenMatrix(matrix) {
  const flat = [];
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      flat.push(matrix[i][j]);
    }
  }
  return flat;
}

/**
 * 计算投影矩阵
 * @param {number} fov
 * @param {number} aspect
 * @param {number} near
 * @param {number} far
 * @returns {number[]}
 */
export function calculateProjectionMatrix(fov, aspect, near, far) {
  const fovRad = (fov * Math.PI) / 180;
  const f = 1.0 / Math.tan(fovRad / 2.0);
  
  return [
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) / (near - far), (2 * far * near) / (near - far),
    0, 0, -1, 0
  ];
} 