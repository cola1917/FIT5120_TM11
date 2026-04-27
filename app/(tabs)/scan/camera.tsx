import { CameraView, useCameraPermissions, type CameraType } from 'expo-camera';
import { router } from 'expo-router';
import React, { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

/*
  DEBUG FLAGS FOR TESTING

  Set these to true temporarily when you want to test failure states:
  - DEBUG_FORCE_CAMERA_UNAVAILABLE: tests "Unable to access camera"
  - DEBUG_FORCE_CAPTURE_FAILURE: tests capture failure before analysis
*/
const DEBUG_FORCE_CAMERA_UNAVAILABLE = false;
const DEBUG_FORCE_CAPTURE_FAILURE = false;

export default function CameraScreen() {
  const insets = useSafeAreaInsets();
  const [facing, setFacing] = useState<CameraType>('back');
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [isTakingPhoto, setIsTakingPhoto] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  const handleFlipCamera = () => {
    setFacing((current) => (current === 'back' ? 'front' : 'back'));
  };

  const handleRetryCamera = () => {
    setCameraError(null);
  };

  const handleTakePhoto = async () => {
    if (!cameraRef.current || isTakingPhoto) return;

    try {
      if (DEBUG_FORCE_CAPTURE_FAILURE) {
        throw new Error('Forced capture failure for testing');
      }

      setIsTakingPhoto(true);

      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.7,
      });

      if (!photo?.uri) {
        Alert.alert('Capture failed', 'Unable to capture photo. Please try again.');
        return;
      }

      router.push({
        pathname: '/scan/analysis',
        params: {
          photoUri: photo.uri,
        },
      });
    } catch (error) {
      Alert.alert('Capture failed', 'Unable to capture photo. Please try again.');
      console.error(error);
    } finally {
      setIsTakingPhoto(false);
    }
  };

  if (!permission) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#B45309" />
        <Text style={styles.feedbackTitle}>Opening camera...</Text>
        <Text style={styles.feedbackText}>
          Please wait while we prepare your Hero Lens.
        </Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={[styles.permissionContainer, { paddingTop: insets.top }]}>
        <View style={styles.permissionCard}>
          <Text style={styles.permissionTitle}>Camera access needed</Text>
          <Text style={styles.permissionText}>
            We need permission to access the device camera so the child can scan food.
          </Text>

          <TouchableOpacity style={styles.primaryButton} onPress={requestPermission}>
            <Text style={styles.primaryButtonText}>GRANT CAMERA ACCESS</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={() => router.back()}>
            <Text style={styles.secondaryButtonText}>GO BACK</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (DEBUG_FORCE_CAMERA_UNAVAILABLE || cameraError) {
    return (
      <View style={[styles.permissionContainer, { paddingTop: insets.top }]}>
        <View style={styles.permissionCard}>
          <Text style={styles.permissionTitle}>Unable to access camera</Text>
          <Text style={styles.permissionText}>
            The camera is not available right now. Please try again.
          </Text>

          <TouchableOpacity style={styles.primaryButton} onPress={handleRetryCamera}>
            <Text style={styles.primaryButtonText}>RETRY</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={() => router.back()}>
            <Text style={styles.secondaryButtonText}>GO BACK</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing={facing}
        onMountError={() => {
          setCameraError('Unable to access camera');
        }}
      />

      <View style={[styles.overlay, { paddingTop: insets.top }]}>
        <View style={styles.topBar}>
          <TouchableOpacity style={styles.topButton} onPress={() => router.back()}>
            <Text style={styles.topButtonText}>Back</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.topButton} onPress={handleFlipCamera}>
            <Text style={styles.topButtonText}>Flip</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.guideWrapper}>
          <View style={styles.scanFrame} />
          <Text style={styles.guideText}>Place the food inside the frame</Text>
        </View>

        <View style={styles.bottomBar}>
          <TouchableOpacity
            style={[styles.captureButton, isTakingPhoto && styles.captureButtonDisabled]}
            onPress={handleTakePhoto}
            disabled={isTakingPhoto}
          >
            <Text style={styles.captureButtonText}>
              {isTakingPhoto ? 'CAPTURING...' : 'CAPTURE'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  camera: {
    flex: 1,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  topButton: {
    backgroundColor: 'rgba(0,0,0,0.45)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999,
  },
  topButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  guideWrapper: {
    alignItems: 'center',
  },
  scanFrame: {
    width: 280,
    height: 280,
    borderWidth: 4,
    borderColor: '#FFFFFF',
    borderRadius: 28,
    backgroundColor: 'transparent',
  },
  guideText: {
    marginTop: 14,
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
    textAlign: 'center',
  },
  bottomBar: {
    alignItems: 'center',
    marginBottom: 24,
  },
  captureButton: {
    backgroundColor: '#B45309',
    minWidth: 220,
    minHeight: 64,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
  },
  captureButtonDisabled: {
    opacity: 0.7,
  },
  captureButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '900',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F6F8EC',
    padding: 24,
  },
  feedbackTitle: {
    marginTop: 14,
    fontSize: 24,
    fontWeight: '900',
    color: '#1F1F1F',
    textAlign: 'center',
  },
  feedbackText: {
    marginTop: 8,
    fontSize: 16,
    lineHeight: 24,
    color: '#555',
    textAlign: 'center',
  },
  permissionContainer: {
    flex: 1,
    backgroundColor: '#F6F8EC',
    justifyContent: 'center',
    padding: 24,
  },
  permissionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 24,
  },
  permissionTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#1F1F1F',
    marginBottom: 10,
    textAlign: 'center',
  },
  permissionText: {
    fontSize: 16,
    color: '#555',
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 22,
  },
  primaryButton: {
    backgroundColor: '#B45309',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
  },
  secondaryButton: {
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#EFE7DF',
  },
  secondaryButtonText: {
    color: '#6B4A2B',
    fontSize: 16,
    fontWeight: '800',
  },
});
