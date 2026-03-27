import React, { useState } from 'react';
import { View, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { Spacing, ComponentSpacing } from '../../constants/Spacing';
import { Button } from '../../components/Button';
import { Display } from '../../components/Typography/Display';
import { Body } from '../../components/Typography/Body';
import { scanFood, ApiError } from '../../services/api';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

/**
 * Scanner Page
 * 
 * Large, colorful buttons for camera and gallery access.
 * Child-friendly error messages and loading states.
 */
export default function Scanner() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const handleImageSelected = async (uri: string) => {
    setIsLoading(true);

    try {
      // Get file info to check size
      const response = await fetch(uri);
      const blob = await response.blob();

      if (blob.size > MAX_FILE_SIZE) {
        Alert.alert(
          'Photo Too Big! 📸',
          'Please choose a smaller photo. Try taking a new one!',
          [{ text: 'OK', style: 'default' }]
        );
        setIsLoading(false);
        return;
      }

      // Upload to backend and get results
      const result = await scanFood(uri);
      
      setIsLoading(false);
      
      // Navigate to results page with data
      router.push({
        pathname: '/scanner/results' as any,
        params: {
          foodName: result.food_name,
          assessmentScore: result.assessment_score,
          healthAssessment: result.assessment,
          nutritionalInfo: JSON.stringify(result.nutritional_info),
          alternatives: JSON.stringify(result.alternatives),
        },
      });
    } catch (error) {
      setIsLoading(false);
      
      // Handle API errors with child-friendly messages
      if (error instanceof ApiError) {
        const title = error.statusCode === 408 
          ? 'Taking Too Long! ⏰'
          : error.statusCode === 0
          ? 'No Internet! 📡'
          : 'Oops! 😕';
        
        Alert.alert(title, error.message, [{ text: 'OK', style: 'default' }]);
      } else {
        Alert.alert(
          'Oops! 😕',
          'Something went wrong. Please try again!',
          [{ text: 'OK', style: 'default' }]
        );
      }
    }
  };

  const takePhoto = async () => {
    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert(
        'Camera Needed 📷',
        'We need access to your camera to take photos of your food!',
        [{ text: 'OK', style: 'default' }]
      );
      return;
    }

    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      await handleImageSelected(result.assets[0].uri);
    }
  };

  const chooseFromGallery = async () => {
    // Request media library permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert(
        'Photos Needed 🖼️',
        'We need access to your photos to help you!',
        [{ text: 'OK', style: 'default' }]
      );
      return;
    }

    // Launch image picker
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      await handleImageSelected(result.assets[0].uri);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Display size="medium" color={Colors.primary}>
            Scan Your Food! 🍔
          </Display>
          <Body size="large" color={Colors.on_surface_variant} style={styles.subtitle}>
            Take a photo or choose from your gallery to learn about your food
          </Body>
        </View>

        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
          <Button
            title="📷 Take a Photo"
            onPress={takePhoto}
            disabled={isLoading}
            style={styles.button}
          />

          <Button
            title="🖼️ Choose from Gallery"
            onPress={chooseFromGallery}
            disabled={isLoading}
            style={styles.button}
          />
        </View>

        {/* Loading State */}
        {isLoading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Body size="large" color={Colors.primary} style={styles.loadingText}>
              Analyzing your food... 🔍
            </Body>
          </View>
        )}

        {/* Instructions */}
        {!isLoading && (
          <View style={styles.instructions}>
            <Body size="medium" color={Colors.on_surface_variant}>
              💡 Tip: Make sure your food is clearly visible in the photo!
            </Body>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  content: {
    flex: 1,
    padding: ComponentSpacing.screen.horizontal,
    justifyContent: 'center',
    gap: Spacing['3xl'],
  },
  header: {
    gap: Spacing.md,
    alignItems: 'center',
  },
  subtitle: {
    textAlign: 'center',
  },
  buttonContainer: {
    gap: Spacing.xl,
  },
  button: {
    width: '100%',
  },
  loadingContainer: {
    alignItems: 'center',
    gap: Spacing.lg,
    padding: Spacing['2xl'],
  },
  loadingText: {
    textAlign: 'center',
  },
  instructions: {
    alignItems: 'center',
    padding: Spacing.lg,
  },
});
