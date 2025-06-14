// vector.js

/**
 * 向量加法
 * @param {number[]} v1
 * @param {number[]} v2
 * @returns {number[]}
 */
export function addVectors(v1, v2) {
  return [v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]];
}

/**
 * 向量减法
 * @param {number[]} v1
 * @param {number[]} v2
 * @returns {number[]}
 */
export function subtractVectors(v1, v2) {
  return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]];
}

/**
 * 向量缩放
 * @param {number[]} v
 * @param {number} scale
 * @returns {number[]}
 */
export function scaleVector(v, scale) {
  return [v[0] * scale, v[1] * scale, v[2] * scale];
}

/**
 * 向量叉积
 * @param {number[]} v1
 * @param {number[]} v2
 * @returns {number[]}
 */
export function crossProduct(v1, v2) {
  return [
    v1[1] * v2[2] - v1[2] * v2[1],
    v1[2] * v2[0] - v1[0] * v2[2],
    v1[0] * v2[1] - v1[1] * v2[0],
  ];
}

/**
 * 向量点积
 * @param {number[]} v1
 * @param {number[]} v2
 * @returns {number}
 */
export function dotProduct(v1, v2) {
  return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2];
}

/**
 * 向量长度
 * @param {number[]} v
 * @returns {number}
 */
export function vectorLength(v) {
  return Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

/**
 * 向量归一化
 * @param {number[]} v
 * @returns {number[]}
 */
export function normalizeVector(v) {
  const length = vectorLength(v);
  if (length === 0) return [0, 0, 0];
  return [v[0] / length, v[1] / length, v[2] / length];
} 